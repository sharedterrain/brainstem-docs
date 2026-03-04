# 🏠 Documentation Mirror System

## First Principles

This system exists to give **external models read access** to canonical Notion docs via durable GitHub URLs. The driving needs:

1. **Security** — Git mirrors are inherently read-only. No external model can mutate the workspace through a GitHub URL. Essential for OpenClaw and any sandboxed agent environment.

1. **Context portability** — A raw GitHub URL works in Claude, ChatGPT, Perplexity, or any tool that accepts URLs. No per-model integration, no auth setup. Switch models mid-session and hand the same URLs.

1. **Token efficiency** — Clean markdown is 3–5× lighter than Notion API JSON for the same content. Cheaper to ingest.

### Why not MCP?

MCP can provide live Notion access, but introduces write permission risk, sequencing problems with concurrent model access, and higher token cost per page. For the "give a model current context" use case, a periodically refreshed Git mirror is simpler, safer, and cheaper. MCP may be revisited later for real-time use cases.

---

## Invariant: Framework vs Projects

- **Framework content** is reusable across projects → repo: [mirror-framework](https://github.com/sharedterrain/mirror-framework)

- **Project content** is project-specific → repo per project (e.g., Brain Stem: [brainstem-docs](https://github.com/sharedterrain/brainstem-docs))

- Never place framework-only docs into a project repo.

**Canonicality Rule:**

- Notion is the managed source of truth for content and planning

- GitHub repos are public mirrors for external AI access

- No content is considered published until mirrored to GitHub

---

## Phase 1: MVP (Trigger-Only Make + GitHub Action)

> ✅ **Status: Built.** v2 architecture is live. Make triggers only; all conversion runs in GitHub Action + Python.

> 🚀 [**Trigger Git Mirror**](https://hook.us2.make.com/mjpxw1t8bt5p0d43tv97yt42v17r6jp3) — fires Make webhook → repository_dispatch → GitHub Action → converts and commits all active pages

### What it does

One button press refreshes all mirrored pages. Make fires a single `repository_dispatch` event to GitHub. A GitHub Action runs a Python script that reads the Export Scope Mapping from Notion, fetches all block content (with full pagination), converts to clean markdown, commits the `.md` files, and writes mirror status back to Notion.

### Architecture (v2 — as-built)

```plain text
Notion Button (webhook)
    → Make.com (2 modules: webhook trigger → HTTP POST repository_dispatch)
        → GitHub Action (.github/workflows/convert.yml)
            → Python script (scripts/notion_to_md.py)
                → Query Export Scope Mapping DB for active rows
                → For each row:
                    → Fetch page title (Notion API)
                    → Fetch all blocks recursively (Notion API, paginated)
                    → Convert blocks to Markdown
                    → Write .md file to repo
                    → Write Mirror Status + Last Mirrored back to Notion
                → Single atomic git commit with [skip ci]
```

### Why v2 replaced v1

The original v1 design placed all transformation logic inside Make: an 11-module scenario that fetched blocks, encoded JSON, and committed per-page inside an iterator loop. This caused:

- **7 simultaneous Git commits** that produced race conditions

- **GitHub Actions cancelling each other** from concurrent pushes

- **Make self-deactivating** on repeated conflicts

- **100-block truncation** because Make lacks native pagination

Each failure was patched incrementally instead of addressing the root cause. v2 moved all transformation to a code environment where pagination, error handling, and atomic commits are trivial. See FR-20260302-001 in the Friction Log and the "Make wires, it does not transform" candidate in Working Agreements.

### Export Scope Mapping

Maintained as a Notion database (see below on this page). The Python script queries it directly via the Notion API, filtering for rows where **Active = true**. Each row maps a source page to an output `.md` path.

**Key columns:** Page Name (title), Active (checkbox), Path (text — target `.md` path), Source Page (url — full Notion page URL), Mirror Status (select: Current/Failed/Never Mirrored/Stale), Last Mirrored (date — written by Python script).

### Make Scenario Spec

**Scenario name:** `Mirror Bulk Publish`

**Trigger:** Custom webhook (fired from Notion button on this page)

**Module 1:** Webhook — receives the trigger

**Module 2:** HTTP POST — sends `repository_dispatch` event to GitHub

```plain text
POST https://api.github.com/repos/sharedterrain/notion-mirror/dispatches
Headers:
  Authorization: Bearer <<GITHUB_TOKEN>>
  Accept: application/vnd.github+json
Body:
  {"event_type": "notion-mirror"}
```

**Total per run:** 2 ops (regardless of page count)

**Monthly at weekly cadence:** ~8 ops

### GitHub Action

**File:** `.github/workflows/convert.yml`

**Repo:** `sharedterrain/notion-mirror`

```yaml
name: convert

on:
  workflow_dispatch:
  repository_dispatch:
    types: [notion-mirror]

permissions:
  contents: write

jobs:
  convert:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install requests

      - name: Run Notion converter
        env:
          NOTION_API_TOKEN: $ secrets.NOTION_API_TOKEN 
        run: python scripts/notion_to_md.py

      - name: Commit converted markdown files
        run: |
          git config user.name "notion-mirror[bot]"
          git config user.email "notion-mirror[bot]@users.noreply.github.com"
          git add .
          git diff --cached --quiet || git commit -m "docs: sync Notion pages to markdown [skip ci]"
          git pull --rebase origin main
          git push
```

### Python Converter

**File:** `scripts/notion_to_md.py`

**Repo:** `sharedterrain/notion-mirror`

Queries the Export Scope Mapping DB for active rows, fetches block content with full pagination (no 100-block limit), converts to clean Markdown, writes `.md` files, and writes Mirror Status + Last Mirrored back to each mapping row.

```python
#!/usr/bin/env python3
"""
notion_to_md.py

Queries the Notion "Export Scope Mapping" database for active rows,
fetches block content for each page (with full pagination),
converts to clean Markdown, and writes .md files to the repo.

Required env vars:
NOTION_API_TOKEN          — Notion integration token
NOTION_EXPORT_SCOPE_DB_ID — optional override; defaults to known DB ID
"""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
import requests

# ── Config ────────────────────────────────────────────────────────────────────

NOTION_TOKEN = os.environ.get("NOTION_API_TOKEN")
if not NOTION_TOKEN:
    print("ERROR: NOTION_API_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

EXPORT_SCOPE_DB_ID = os.environ.get(
    "NOTION_EXPORT_SCOPE_DB_ID", "38f8657d2479419599377864111fea70"
)

NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

REPO_ROOT = Path(__file__).parent.parent

# ── Export Scope query ────────────────────────────────────────────────────────

def fetch_export_scope() -> list:
    """Query the Export Scope Mapping DB for all active rows."""
    url = f"https://api.notion.com/v1/databases/{EXPORT_SCOPE_DB_ID}/query"
    payload = {"filter": {"property": "Active", "checkbox": {"equals": True}}}
    pages = []

    while True:
        r = requests.post(url, headers=HEADERS, json=payload)
        r.raise_for_status()
        data = r.json()

        for row in data.get("results", []):
            props = row.get("properties", {})

            name_parts = props.get("Page Name", {}).get("title", [])
            name = "".join(p.get("plain_text", "") for p in name_parts)

            path_parts = props.get("Path", {}).get("rich_text", [])
            path = "".join(p.get("plain_text", "") for p in path_parts)

            source_url = (props.get("Source Page", {}).get("url") or "").replace("-", "")
            match = re.search(r"([a-f0-9]{32})$", source_url)
            page_id = match.group(1) if match else ""

            if not page_id or not path:
                print(f"  SKIP — missing page_id or path for row: {name!r}")
                continue

            pages.append({"name": name, "page_id": page_id, "path": path, "row_id": row["id"]})

        if data.get("has_more"):
            payload["start_cursor"] = data["next_cursor"]
        else:
            break

    return pages

# ── Notion API helpers ────────────────────────────────────────────────────────

def update_mirror_status(row_id: str, status: str) -> None:
    """Write Mirror Status and Last Mirrored back to the Export Scope Mapping row."""
    url = f"https://api.notion.com/v1/pages/{row_id}"
    payload = {
        "properties": {
            "Mirror Status": {"select": {"name": status}},
            "Last Mirrored": {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}}
        }
    }
    requests.patch(url, headers=HEADERS, json=payload)

def fetch_page_title(page_id: str) -> str:
    url = f"https://api.notion.com/v1/pages/{page_id}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    props = r.json().get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(p.get("plain_text", "") for p in parts)
    return page_id

def fetch_blocks(block_id: str) -> list:
    """Fetch all block children with full pagination, recursing into nested blocks."""
    blocks = []
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    params = {"page_size": 100}

    while True:
        r = requests.get(url, headers=HEADERS, params=params)
        r.raise_for_status()
        data = r.json()
        blocks.extend(data.get("results", []))
        if data.get("has_more"):
            params["start_cursor"] = data["next_cursor"]
        else:
            break

    for block in blocks:
        if block.get("has_children"):
            block["_children"] = fetch_blocks(block["id"])
        else:
            block["_children"] = []

    return blocks

# ── Rich text helpers ─────────────────────────────────────────────────────────

def rich_text_to_md(rich_texts: list) -> str:
    parts = []
    for rt in rich_texts:
        text = rt.get("plain_text", "")
        if not text:
            continue
        ann = rt.get("annotations", {})
        href = rt.get("href")

        if ann.get("code"):
            text = f"`{text}`"
        else:
            if ann.get("bold") and ann.get("italic"):
                text = f"***{text}***"
            elif ann.get("bold"):
                text = f"**{text}**"
            elif ann.get("italic"):
                text = f"*{text}*"
            if ann.get("strikethrough"):
                text = f"~~{text}~~"
            if ann.get("underline"):
                text = f"<u>{text}</u>"

        if href:
            text = f"[{text}]({href})"

        parts.append(text)
    return "".join(parts)

# ── Block-to-Markdown conversion ──────────────────────────────────────────────

def block_to_md(block: dict, depth: int = 0) -> str:
    btype = block.get("type", "")
    data = block.get(btype, {})
    children = block.get("_children", [])
    indent = "    " * depth
    lines = []

    if btype == "heading_1":
        lines.append(f"# {rich_text_to_md(data.get('rich_text', []))}")
    elif btype == "heading_2":
        lines.append(f"## {rich_text_to_md(data.get('rich_text', []))}")
    elif btype == "heading_3":
        lines.append(f"### {rich_text_to_md(data.get('rich_text', []))}")
    elif btype == "paragraph":
        text = rich_text_to_md(data.get("rich_text", []))
        lines.append(text if text else "")
    elif btype == "bulleted_list_item":
        lines.append(f"{indent}- {rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            lines.append(block_to_md(child, depth + 1))
    elif btype == "numbered_list_item":
        lines.append(f"{indent}1. {rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            lines.append(block_to_md(child, depth + 1))
    elif btype == "to_do":
        checked = "x" if data.get("checked") else " "
        lines.append(f"{indent}- [{checked}] {rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            lines.append(block_to_md(child, depth + 1))
    elif btype == "toggle":
        text = rich_text_to_md(data.get("rich_text", []))
        lines.append(f"{indent}<details><summary>{text}</summary>")
        lines.append("")
        for child in children:
            lines.append(block_to_md(child, depth + 1))
        lines.append("")
        lines.append(f"{indent}</details>")
    elif btype == "quote":
        lines.append(f"> {rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            for line in block_to_md(child, 0).splitlines():
                lines.append(f"> {line}")
    elif btype == "callout":
        icon = ""
        icon_data = data.get("icon", {})
        if icon_data.get("type") == "emoji":
            icon = icon_data.get("emoji", "") + " "
        lines.append(f"> {icon}{rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            for line in block_to_md(child, 0).splitlines():
                lines.append(f"> {line}")
    elif btype == "code":
        lang = data.get("language", "")
        lines.append(f"```{lang}")
        lines.append(rich_text_to_md(data.get("rich_text", [])))
        lines.append("```")
    elif btype == "divider":
        lines.append("---")
    elif btype == "table_of_contents":
        lines.append("<!-- table_of_contents -->")
    elif btype == "table":
        rows = []
        for child in children:
            cells = child.get("table_row", {}).get("cells", [])
            rows.append([rich_text_to_md(cell) for cell in cells])
        if rows:
            col_count = max(len(r) for r in rows)
            rows = [r + [""] * (col_count - len(r)) for r in rows]
            lines.append("| " + " | ".join(rows[0]) + " |")
            lines.append("| " + " | ".join(["---"] * col_count) + " |")
            for row in rows[1:]:
                lines.append("| " + " | ".join(row) + " |")
    elif btype == "table_row":
        pass
    elif btype == "image":
        url = (data.get("external") or data.get("file") or {}).get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        lines.append(f"![{caption}]({url})")
        if caption:
            lines.append(f"*{caption}*")
    elif btype in ("video", "file", "pdf", "audio"):
        url = (data.get("external") or data.get("file") or {}).get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        lines.append(f"[{caption or btype}]({url})")
    elif btype in ("embed", "bookmark", "link_preview"):
        url = data.get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        lines.append(f"[{caption or url}]({url})")
    elif btype == "child_page":
        lines.append(f"**Child page:** {data.get('title', '')}")
    elif btype == "child_database":
        lines.append(f"**Child database:** {data.get('title', '')}")
    elif btype in ("column_list", "column", "synced_block"):
        for child in children:
            lines.append(block_to_md(child, depth))
    elif btype == "breadcrumb":
        lines.append("<!-- breadcrumb -->")
    elif btype == "template":
        lines.append(f"<!-- template: {rich_text_to_md(data.get('rich_text', []))} -->")
    elif btype == "equation":
        lines.append(f"$${data.get('expression', '')}$$")
    else:
        lines.append(f"<!-- unsupported block type: {btype} -->")

    return "\n".join(lines)

def blocks_to_md(blocks: list) -> str:
    sections = [block_to_md(b) for b in blocks]
    raw = "\n\n".join(sections)
    return re.sub(r"\n{3,}", "\n\n", raw).strip() + "\n"

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Querying Export Scope Mapping DB...")
    pages = fetch_export_scope()

    if not pages:
        print("No active pages found — nothing to convert.")
        return

    print(f"Converting {len(pages)} pages...")
    errors = []

    for entry in pages:
        page_id = entry["page_id"]
        path = entry["path"]
        name = entry["name"]
        row_id = entry["row_id"]
        print(f"  → {name}  ({path})")

        try:
            title = fetch_page_title(page_id)
            blocks = fetch_blocks(page_id)
            md_content = f"# {title}\n\n{blocks_to_md(blocks)}"

            out_path = REPO_ROOT / path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md_content, encoding="utf-8")
            print(f"     ✓ {out_path.relative_to(REPO_ROOT)}")
            update_mirror_status(row_id, "Current")

        except requests.HTTPError as e:
            msg = f"HTTP {e.response.status_code} — {page_id} ({name})"
            print(f"     ✗ {msg}", file=sys.stderr)
            errors.append(msg)
            update_mirror_status(row_id, "Failed")
        except Exception as e:
            msg = f"Error — {page_id} ({name}): {e}"
            print(f"     ✗ {msg}", file=sys.stderr)
            errors.append(msg)
            update_mirror_status(row_id, "Failed")

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\nAll pages converted successfully.")

if __name__ == "__main__":
    main()
```

### Supported block types

The converter handles: headings (1-3), paragraphs, bulleted/numbered lists, to-do items, toggles, quotes, callouts, code blocks, dividers, tables, images, video/file/pdf/audio embeds, bookmarks, equations, columns, synced blocks, child pages/databases (as labels), and table of contents. Unsupported block types render as HTML comments.

### Placeholders

- `<<NOTION_TOKEN>>` — Integration token. Stored device-only + as `NOTION_API_TOKEN` GitHub Secret in `sharedterrain/notion-mirror`

- `<<GITHUB_TOKEN>>` — Personal access token (repo scope, `sharedterrain/notion-mirror`). Expires May 25, 2026. Used by Make Module 2 for `repository_dispatch`

- `<<MAKE_WEBHOOK_URL>>` — Webhook URL for the bulk publish trigger

### Staleness Checker (Cron)

A daily GitHub Actions cron job that does two things:

1. **Resolves empty Source Page URLs** — searches Notion by Page Name title, writes the matching page URL back to the Source Page column. This means you only need to fill in Page Name and Path when adding rows; the script populates Source Page automatically on the next run.

1. **Checks staleness** — fetches `last_edited_time` from Notion for each source page and writes it to the **Last Updated** column. If Last Updated > Last Mirrored, the doc is stale.

No manual stamping, no manual URL pasting, works for every page in the mapping.

**File:** `.github/workflows/staleness.yml`

**Repo:** `sharedterrain/notion-mirror`

```yaml
name: Check Mirror Staleness

on:
  schedule:
    - cron: "0 14 * * *" # 6am PT daily
  workflow_dispatch:

jobs:
  staleness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install requests

      - run: python scripts/check_staleness.py
        env:
          NOTION_API_TOKEN: $ secrets.NOTION_API_TOKEN 
```

**File:** `scripts/check_staleness.py`

**Repo:** `sharedterrain/notion-mirror`

```python
#!/usr/bin/env python3
"""
check_staleness.py

Two jobs in one script:
1. Resolve empty Source Page URLs by searching the Notion API by title
2. Fetch last_edited_time for each source page and write it to "Last Updated"

Staleness rule: if Last Updated > Last Mirrored, the doc
has been edited since its last mirror run.

Required env vars:
  NOTION_API_TOKEN          — Notion integration token
  NOTION_EXPORT_SCOPE_DB_ID — optional override; defaults to known DB ID
"""

import os
import re
import sys
import requests

# ── Config ────────────────────────────────────────────────────────────────────

NOTION_TOKEN = os.environ.get("NOTION_API_TOKEN")
if not NOTION_TOKEN:
    print("ERROR: NOTION_API_TOKEN environment variable not set.", file=sys.stderr)
    sys.exit(1)

EXPORT_SCOPE_DB_ID = os.environ.get(
    "NOTION_EXPORT_SCOPE_DB_ID", "38f8657d2479419599377864111fea70"
)

NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

# ── Export Scope query ────────────────────────────────────────────────────────

def fetch_active_rows() -> list:
    """Query the Export Scope Mapping DB for all active rows.
    Returns rows with name, row_id, and source_url (may be empty)."""
    url = f"https://api.notion.com/v1/databases/{EXPORT_SCOPE_DB_ID}/query"
    payload = {"filter": {"property": "Active", "checkbox": {"equals": True}}}
    rows = []

    while True:
        r = requests.post(url, headers=HEADERS, json=payload)
        r.raise_for_status()
        data = r.json()

        for row in data.get("results", []):
            props = row.get("properties", {})

            name_parts = props.get("Page Name", {}).get("title", [])
            name = "".join(p.get("plain_text", "") for p in name_parts)

            source_url = (props.get("Source Page", {}).get("url") or "")

            rows.append({
                "name": name,
                "source_url": source_url,
                "last_mirrored": (props.get("Last Mirrored", {}).get("date") or {}).get("start", ""),
                "row_id": row["id"],
            })

        if data.get("has_more"):
            payload["start_cursor"] = data["next_cursor"]
        else:
            break

    return rows

def extract_page_id(source_url: str) -> str:
    """Extract 32-char hex page ID from a Notion URL."""
    clean = source_url.replace("-", "")
    match = re.search(r"([a-f0-9]{32})$", clean)
    return match.group(1) if match else ""

# ── Source Page resolution ────────────────────────────────────────────────────

def search_page_by_title(title: str) -> dict | None:
    """Search Notion for a page matching the given title exactly.
    Returns {url, page_id} or None if no exact match found."""
    url = "https://api.notion.com/v1/search"
    payload = {
        "query": title,
        "filter": {"value": "page", "property": "object"},
        "page_size": 10,
    }
    r = requests.post(url, headers=HEADERS, json=payload)
    r.raise_for_status()

    for result in r.json().get("results", []):
        props = result.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                parts = prop.get("title", [])
                result_title = "".join(p.get("plain_text", "") for p in parts)
                if result_title.strip() == title.strip():
                    return {
                        "url": result.get("url", ""),
                        "page_id": result["id"],
                    }
    return None

def write_source_page(row_id: str, page_url: str) -> None:
    """Write a resolved Notion page URL to the Source Page column."""
    url = f"https://api.notion.com/v1/pages/{row_id}"
    payload = {
        "properties": {
            "Source Page": {"url": page_url}
        }
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    r.raise_for_status()

# ── Staleness helpers ─────────────────────────────────────────────────────────

def fetch_last_edited_time(page_id: str) -> str:
    """Fetch last_edited_time from Notion page metadata."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json().get("last_edited_time", "")

def write_last_updated(row_id: str, last_edited: str) -> None:
    """Write last_edited_time to the Last Updated column."""
    url = f"{{https://api.notion.com/v1/pages/{row_id}}}"
    payload = {
        "properties": {
            "Last Updated": {
                "date": {"start": last_edited}
            }
        }
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    r.raise_for_status()
def write_mirror_status(row_id: str, status: str) -> None:
    """Write Mirror Status (e.g. 'Stale') to the Export Scope Mapping row."""
    url = f"{{https://api.notion.com/v1/pages/{row_id}}}"
    payload = {
        "properties": {
            "Mirror Status": {"select": {"name": status}}
        }
    }
    r = requests.patch(url, headers=HEADERS, json=payload)
    r.raise_for_status()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Fetching active rows from Export Scope Mapping...")
    rows = fetch_active_rows()

    if not rows:
        print("No active rows found.")
        return

    # ── Pass 1: Resolve empty Source Page URLs ────────────────────────────
    empty_source = [r for r in rows if not r["source_url"]]
    if empty_source:
        print(f"\nResolving {len(empty_source)} empty Source Page URL(s)...")
        for row in empty_source:
            name = row["name"]
            try:
                result = search_page_by_title(name)
                if result:
                    write_source_page(row["row_id"], result["url"])
                    row["source_url"] = result["url"]
                    print(f"  ✓ {name} → {result['url']}")
                else:
                    print(f"  ✗ {name} — no exact title match found")
            except Exception as e:
                print(f"  ✗ {name} — {e}", file=sys.stderr)

    # ── Pass 2: Check staleness ───────────────────────────────────────────
    print(f"\nChecking {len(rows)} pages for staleness...")
    errors = []

    for row in rows:
        page_id = extract_page_id(row["source_url"])
        row_id = row["row_id"]
        name = row["name"]

        if not page_id:
            print(f"  SKIP — no page_id for: {name!r}")
            continue

        try:
            last_edited = fetch_last_edited_time(page_id)
            if not last_edited:
                print(f"  SKIP — no last_edited_time for: {name!r}")
                continue

            write_last_updated(row_id, last_edited)
            # Compare last_edited vs last_mirrored to set Mirror Status
            last_mirrored = row["last_mirrored"]
            if not last_mirrored or last_edited > last_mirrored:
                write_mirror_status(row_id, "Stale")
                print(f"  ✓ {name} — last edited {last_edited} → STALE")
            else:
                print(f"  ✓ {name} — last edited {last_edited} → current")

        except requests.HTTPError as e:
            msg = f"HTTP {e.response.status_code} — {name} ({page_id})"
            print(f"  ✗ {msg}", file=sys.stderr)
            errors.append(msg)
        except Exception as e:
            msg = f"Error — {name}: {e}"
            print(f"  ✗ {msg}", file=sys.stderr)
            errors.append(msg)

    if errors:
        print(f"\n{len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\nAll pages checked.")

if __name__ == "__main__":
    main()
```

**How staleness works:** The cron writes Notion's `last_edited_time` to Last Updated. The mirror script writes `now()` to Last Mirrored. If Last Updated > Last Mirrored, the source has been edited since the last mirror — it's stale. Source Page URLs are auto-resolved on each run, so new rows only need Page Name and Path.

---

### What's explicitly deferred

- CI checks on generated markdown

- Friction DB integration and Slack capture

- Promotion rituals and drift control

- Sessions DB

- Per-page publish buttons (bulk covers the need)

- Budget guardrails automation (manual tracking is fine at this volume)

- Status writeback design (currently handled by Python script; separate mechanism TBD)

---

## Future Phases (Reference Material)

The following child pages contain detailed designs for the full mirror system vision. They are **not in active scope** but are preserved for future phases.

**Child page:** 📦 Framework (Governance & CI)
## Purpose
Reusable governance, CI, and mirror protocols for any project using the Notion → GitHub mirror system. This framework can be adopted by multiple projects to maintain consistent publish-safety and drift control.
Framework content must be reusable across projects; project-specific snapshots belong under Projects/<project>.
## GitHub Source
[https://github.com/sharedterrain/mirror-framework](https://github.com/sharedterrain/mirror-framework)
## Framework File Map
- .github/workflows/validate.yml
- checks/scan_secrets.sh
- automation/redaction_patterns.txt
- contracts/spec.yaml
- contracts/routes.yaml
- contracts/AI_COLLABORATION.md
- protocols/PUBLISHING.md
- protocols/SECURITY.md
- protocols/ADOPT_THIS_FRAMEWORK.md
- CONTRACT.md
- README.md
## Framework Pages
**Child page:** Mirror Publishing Rules (Framework)
**Status:** [Mirrored to GitHub]
**GitHub Path:** `framework/MIRROR_PUBLISHING_`[`RULES.md`](http://rules.md/)
---
## Canonicality
- Notion is the **managed Source of Truth** for all content and planning
- GitHub repos are **PUBLIC MIRRORS** for external AI access
- GitHub is the **ENFORCEMENT BOUNDARY** via CI gates and branch workflow
- No content is considered "published" until it is mirrored to GitHub AND passes CI
## Publish Scope
Content eligible for public mirror:
- `/contracts/` – All governance and schema files
- `/protocols/` – All operating procedures
- `/phases/` – All build phase documentation
- `/changelog/` – All change log entries
- [`CONTRACT.md`](http://contract.md/) – Root governance contract
- [`README.md`](http://readme.md/) – Public repo entry point
Content NOT mirrored (Notion-only):
- Configuration Registry (sensitive config)
- Internal operational Drift Log (working notes)
- Work-in-progress pages without explicit publish flag
- Daily logs and scratch pages
## Placeholder Format
All sensitive values in mirrored docs must use placeholder format:
```javascript
<<ALL_CAPS_WITH_UNDERSCORES>>
```
**Examples:**
- `<<SLACK_WEBHOOK_URL>>`
- `<<AIRTABLE_API_KEY>>`
- `<<PERPLEXITY_TOKEN>>`
- `<<GITHUB_PAT>>`
## EXAMPLE_SECRET Rule
Intentional examples of secret-like patterns are allowed IF AND ONLY IF they contain the exact marker string on the same line:
```javascript
EXAMPLE_SECRET:
```
**Example usage:**
```bash
# This will pass CI:
curl -H "Authorization: Bearer abc123def456" EXAMPLE_SECRET: https://api.example.com

# This will FAIL CI (no marker):
curl -H "Authorization: Bearer abc123def456" https://api.example.com
```
**Rule:** The marker must appear on the SAME LINE as the secret-like pattern.
## Required Workflow
1. All changes flow: **Notion** → export → **dev branch** → PR → **main**
1. CI gate (`scan-secrets`) must pass before merge to main
1. Authoritative secret patterns: `automation/redaction_patterns.txt`
1. Branch protection on main: PRs required, status checks required, must be up-to-date
1. Agent branches use format: `agent/<name>-<topic>`
## CI Enforcement
- `checks/scan_`[`secrets.sh`](http://secrets.sh/) runs on every PR
- Script reads patterns from `automation/redaction_patterns.txt`
- Scanner excludes `automation/redaction_patterns.txt` (self-match prevention)
- Any line containing `EXAMPLE_SECRET:` is ignored by scanner
- Failures block merge; fix in dev branch and push
## Publication Gate
Content is published when:
- [ ] Exported from Notion
- [ ] Committed to dev branch
- [ ] PR created (dev → main)
- [ ] CI check `scan-secrets` passes ✅
- [ ] PR merged to main
- [ ] Entry recorded in Public Drift Log
Until all steps complete, content remains **UNPUBLISHED**.
## File Path Conventions
**Exact paths (no variations):**
- `checks/scan_`[`secrets.sh`](http://secrets.sh/)
- `automation/redaction_patterns.txt`
- `contracts/spec.yaml`
- `contracts/routes.yaml`
- `contracts/AI_`[`COLLABORATION.md`](http://collaboration.md/)
- `changelog/` (directory, NOT [`CHANGELOG.md`](http://changelog.md/))
- [`CONTRACT.md`](http://contract.md/) (root, NOT `contracts/`[`CONTRACT.md`](http://contract.md/))
## Reuse and Portability
- Framework CI scripts should be **copied** or included via **Git submodule**
- Do NOT assume symlink support (GitHub Actions portability)
- Each project repo copies framework validation scripts at setup
**Child page:** Drift Control Procedure (Framework)
**Status:** [Mirrored to GitHub]
**GitHub Path:** `framework/DRIFT_CONTROL_`[`PROCEDURE.md`](http://procedure.md/)
---
## Canonicality Rules
**Source of Truth hierarchy:**
1. **Notion** = managed Source of Truth for content and planning
1. **GitHub** = public mirror + enforcement gate (CI validates what gets published)
1. **Drift Log** = reconciliation record (Notion operational + GitHub public)
**Resolution priority when conflicts arise:**
- Notion wins for content and planning decisions
- GitHub repo wins for actual CI behavior and script correctness
- If CI rules changed directly in repo, update Notion to document actual behavior
## How to Avoid Drift
### Before Mirroring
- [ ] Verify Notion page is marked for mirror export
- [ ] Check that page matches governance rules in `contracts/spec.yaml`
- [ ] Replace all sensitive values with `<<PLACEHOLDER_FORMAT>>`
- [ ] Add `EXAMPLE_SECRET:` marker to any intentional secret examples
- [ ] Verify target GitHub path is documented on Notion page
### During Export
- [ ] Export affected Notion pages to markdown
- [ ] Commit to dev branch with descriptive message
- [ ] Create PR (dev → main)
- [ ] Confirm CI `scan-secrets` passes
- [ ] Do NOT merge if checks fail
### After Merge
- [ ] Record entry in operational Drift Log (Notion)
- [ ] Record entry in Public Drift Log (GitHub)
- [ ] Update "Currently Published" tracker
- [ ] Archive local export files
## Drift Detection Rules
**Record a drift entry when:**
- Notion page exported and mirrored to repo
- CI check definition updated
- Governance rule changed in `contracts/`
- Protocol or phase doc updated
- Manual reconciliation performed (Notion ↔ repo mismatch fixed)
**Drift is detected when:**
- Notion page content differs from corresponding repo file
- Repo file exists but no corresponding Notion page (orphan)
- Notion page flagged for publish but not in repo (missing mirror)
- Notion page metadata (GitHub Path) doesn't match actual repo structure
## Canonical Rules Mapping
| Notion Location | GitHub Location | Purpose |
| --- | --- | --- |
| CONTRACT (Project) | [`CONTRACT.md`](http://contract.md/) | Root governance contract |
| contracts/spec (Project) | `contracts/spec.yaml` | Mirror governance spec |
| contracts/routes (Project) | `contracts/routes.yaml` | Routing schema |
| AI Collaboration Contract | `contracts/AI_`[`COLLABORATION.md`](http://collaboration.md/) | Agent operating rules |
| Protocols (Project) | `protocols/` | Operating procedures |
| Build Phases (Project) | `phases/` | Phase documentation |
| Changelog (Project) | `changelog/` | Change entries |
| Secret Scan Script | `checks/scan_`[`secrets.sh`](http://secrets.sh/) | CI validation |
| Redaction Patterns | `automation/redaction_patterns.txt` | Secret patterns |
| Public Drift Log | `DRIFT_`[`LOG.md`](http://log.md/) | Public reconciliation record |
## Recording Changes
### Operational Drift Log (Notion-only)
Internal working notes for tracking mirror operations.
**Entry format:**
```javascript
## [YYYY-MM-DD] – [Change Summary]

**Notion Pages:** [links]
**GitHub PR:** [PR URL]
**Commit:** [hash]
**Status:** [merged/blocked/pending]
**Notes:** [internal context]
```
### Public Drift Log (Mirrored to GitHub)
External-facing record for AI/human verification of mirror alignment.
**Entry format:** See Public Drift Log template page.
## Page Mirror Status Indicators
**Every Notion page must clearly indicate:**
- **Status:** `[Mirrored to GitHub]` or `[Notion-only]`
- **GitHub Path:** (if mirrored) exact relative path in repo
- **Last Mirror Date:** (if mirrored) ISO date of last successful sync
**Example banner:**
```javascript
**Status:** [Mirrored to GitHub]
**GitHub Path:** `contracts/spec.yaml`
**Last Mirror Date:** 2026-02-06
```
## Reconciliation Checklist
Run this checklist monthly or after major mirror operations:
- [ ] Compare Notion "Currently Published" tracker to actual repo `main` branch
- [ ] Verify all Notion pages marked `[Mirrored to GitHub]` exist in repo
- [ ] Verify all repo files have corresponding Notion source pages
- [ ] Check Public Drift Log entries match operational Drift Log
- [ ] Scan for orphaned files (in repo but no Notion source)
- [ ] Scan for missing mirrors (Notion page marked for mirror but not in repo)
- [ ] Verify CI patterns file matches documented patterns in Notion
- [ ] Confirm EXAMPLE_SECRET rule is documented consistently
**Child page:** Operational Drift Log (Notion-only) (Framework)
**Status:** [Notion-only]
**Purpose:** Operational record of Notion → GitHub mirror synchronization for internal tracking
**Note:** No public drift log file exists in the GitHub mirror in Stage 2.
---
# Public Drift Log
This log records all changes mirrored from Notion to this GitHub repository. External AIs can use this log to verify alignment between Notion (canonical source) and GitHub (public mirror).
**Recording Rule:** Every mirrored change must add an entry below.
---
## Entry Template
```markdown
## [YYYY-MM-DD] – [Change Summary]

**Date:** YYYY-MM-DD  
**Change Summary:** Brief description of what changed  

**Notion Pages Affected:**
- Page Title (Notion URL if public)
- Page Title (Notion URL if public)

**GitHub PR:** https://github.com/owner/repo/pull/###  
**Commit Hash:** abc1234  

**Checks Passed:**
- [x] scan-secrets
- [x] [other required checks]

**Files Changed:**
- `contracts/spec.yaml`
- `protocols/operating_protocol.md`

**Notes:**
- Any notable context for external reviewers
- Breaking changes or schema updates
- Dependencies on other changes

---
```
## Required Fields
- **Date:** ISO format (YYYY-MM-DD)
- **Change Summary:** One-line description
- **Notion Pages Affected:** List of source pages (use public Notion URLs if available)
- **GitHub PR:** Full PR URL
- **Commit Hash:** Short hash (7+ chars)
- **Checks Passed:** List of CI checks that passed
- **Files Changed:** Relative paths of modified files
- **Notes:** Context for external readers
## Entry Rules
1. Add entries in **reverse chronological order** (newest first)
1. One entry per PR merge (even if multiple Notion pages)
1. Include entry BEFORE marking content as "published" in Notion
1. If CI fails and blocks merge, do NOT add entry until PR passes and merges
1. If manual reconciliation fixes drift, add entry explaining the fix
## Verification Use Cases
External AIs use this log to:
- Verify a Notion page has been successfully mirrored
- Check when a governance rule was last updated
- Trace a file back to its Notion source
- Detect drift between Notion and GitHub
- Understand the timeline of contract or protocol changes
## Drift Detection
**Drift exists if:**
- A file in `main` branch has no corresponding entry in this log
- Latest log entry date is older than latest commit to a mirrored file
- Notion page claims to be mirrored but no entry exists
**Resolution:**
- Run reconciliation procedure (see Drift Control Procedure)
- Add corrective entry to this log
- Update Notion pages with correct mirror status
---
## Example Entry
```markdown
## 2026-02-05 – Initial CI Secret Scan Implementation

**Date:** 2026-02-05  
**Change Summary:** Added secret scan CI check with EXAMPLE_SECRET escape rule  

**Notion Pages Affected:**
- Mirror Publishing Rules
- CI Checks Documentation

**GitHub PR:** https://github.com/sharedterrain/brainstem-docs/pull/12  
**Commit Hash:** a1b2c3d  

**Checks Passed:**
- [x] scan-secrets

**Files Changed:**
- `checks/scan_secrets.sh`
- `automation/redaction_patterns.txt`
- `contracts/AI_COLLABORATION.md`

**Notes:**
- Implemented EXAMPLE_SECRET: marker to allow intentional examples
- Tightened patterns to avoid false positives on "pat" and "secret_" prefixes
- Scanner now excludes automation/redaction_patterns.txt (self-match prevention)

---
```
**Child page:** CI Checks Documentation (Framework)
**Status:** [Mirrored to GitHub]
**GitHub Path:** `framework/CI_`[`CHECKS.md`](http://checks.md/)
---
## Overview
This page documents the CI validation checks required for all documentation mirror projects.
## Secret Scan Check
**Script:** `checks/scan_`[`secrets.sh`](http://secrets.sh/)  
**Purpose:** Prevent accidental exposure of API keys, tokens, webhooks, and other sensitive values  
**Status:** REQUIRED (blocks merge on failure)  
### How It Works
1. Reads patterns from `automation/redaction_patterns.txt`
1. Scans all files in repo (except excluded paths)
1. Ignores any line containing `EXAMPLE_SECRET:` marker
1. Excludes `automation/redaction_patterns.txt` (self-match prevention)
1. Fails if any pattern match found
### Pattern File Location
**Authoritative source:** `automation/redaction_patterns.txt`
**Format:**
```javascript
pattern1
pattern2
pattern3
```
### EXAMPLE_SECRET Escape Rule
**Marker:** `EXAMPLE_SECRET:`
**Usage:** Place on the SAME LINE as any intentional secret-like example:
```bash
# PASS:
curl -H "Authorization: Bearer abc123" EXAMPLE_SECRET: https://api.example.com

# FAIL (no marker):
curl -H "Authorization: Bearer abc123" https://api.example.com
```
### Excluded Paths
The scanner excludes:
- `automation/redaction_patterns.txt` (self-match prevention)
- `.git/` directory
- Any paths specified in script's exclude list
### Common Patterns
Typical patterns include:
- `xoxb-` (Slack bot tokens)
- `xoxp-` (Slack user tokens)
- [`https://hooks.slack.com/services/`](https://hooks.slack.com/services/) (Slack webhooks)
- API keys with specific prefixes
- JWT tokens
- GitHub personal access tokens
**Note:** See actual `automation/redaction_patterns.txt` in each project repo for authoritative list.
### Failure Resolution
If `scan-secrets` fails:
1. Identify the line triggering the failure (check CI logs)
1. Choose resolution:
    - **Option A:** Replace sensitive value with `<<PLACEHOLDER_FORMAT>>`
    - **Option B:** Add `EXAMPLE_SECRET:` marker to the line if it's an intentional example
    - **Option C:** Remove the line if it's not needed
1. Commit fix to dev branch
1. Push to update PR
1. Verify check passes before merge
## Future Checks
**Potential additions:**
- Markdown link validation
- YAML schema validation for contracts
- Broken reference detection
- Placeholder format validation
## Integration with Projects
**Setup for new project:**
1. Copy `checks/scan_`[`secrets.sh`](http://secrets.sh/) from framework
1. Copy `automation/redaction_patterns.txt` from framework (or extend)
1. Add GitHub Actions workflow:
```yaml
name: Validate Docs

on:
  pull_request:
    branches: [main]

jobs:
  scan-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Scan for secrets
        run: bash checks/scan_secrets.sh
```
1. Enable branch protection on `main` branch
1. Require `scan-secrets` status check to pass
## Portability Notes
- Do NOT use symlinks (GitHub Actions portability issue)
- Use **copy** or **Git submodule** for script reuse
- Each project repo should have its own `checks/` directory
- Framework updates propagate via manual copy or submodule update
**Child page:** Automation Config Documentation (Framework)
**Status:** [Mirrored to GitHub]
**GitHub Path:** `framework/AUTOMATION_`[`CONFIG.md`](http://config.md/)
---
## Overview
This page documents the automation configuration files used across all documentation mirror projects.
## Redaction Patterns File
**Location:** `automation/redaction_patterns.txt`  
**Purpose:** Authoritative list of secret patterns for CI scan  
**Format:** Plain text, one pattern per line  
### File Structure
```javascript
# Comments allowed (lines starting with #)
pattern1
pattern2
pattern3
```
### Core Framework Patterns
Minimum patterns for all projects:
```javascript
xoxb-
xoxp-
https://hooks.slack.com/services/
sk-
Bearer [A-Za-z0-9_-]{20,}
Authorization: Bearer
```
### Project-Specific Patterns
Each project may extend the core patterns:
**Brain Stem example additions:**
```javascript
secret_[a-z_]+=[A-Za-z0-9_-]{10,}
API_KEY=[A-Za-z0-9_-]{20,}
```
### Pattern Syntax
- Plain text strings match literally
- Regex patterns supported (varies by scan script implementation)
- Case-sensitive by default
- Whitespace matters
### Self-Exclusion Rule
**Important:** The scanner MUST exclude `automation/redaction_patterns.txt` to avoid self-matching.
**Reason:** The patterns file contains secret-like strings by definition.
**Implementation:** `checks/scan_`[`secrets.sh`](http://secrets.sh/) hard-codes exclusion of this file.
### Pattern Update Procedure
**To add a new pattern:**
1. Update `automation/redaction_patterns.txt` in Notion documentation
1. Export to dev branch
1. Test locally: `bash checks/scan_`[`secrets.sh`](http://secrets.sh/)
1. Create PR (dev → main)
1. Verify CI passes
1. Merge to main
1. Record in Public Drift Log
**To remove a pattern:**
1. Verify no active docs depend on the pattern
1. Remove from `automation/redaction_patterns.txt` in Notion
1. Follow same PR workflow as above
## GitHub Actions Workflow
**Location:** `.github/workflows/validate.yml`  
**Purpose:** Run CI checks on every PR  
### Template
```yaml
name: Validate Docs

on:
  pull_request:
    branches: [main]
  push:
    branches: [dev]

jobs:
  scan-secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Scan for secrets
        run: bash checks/scan_secrets.sh
```
### Branch Protection Setup
**Required settings for **`main`** branch:**
- [x] Require pull request before merging
- [x] Require status checks to pass before merging
- [x] Require branches to be up to date before merging
- [x] Required status check: `scan-secrets`
- [ ] Require approvals (optional, recommended for team projects)
## Placeholder Format Standard
**Format:** `<<ALL_CAPS_WITH_UNDERSCORES>>`
**Examples:**
- `<<SLACK_WEBHOOK_URL>>`
- `<<AIRTABLE_API_KEY>>`
- `<<GITHUB_PAT>>`
- `<<DATABASE_CONNECTION_STRING>>`
**Rules:**
- All caps
- Underscores for word separation
- No hyphens or other delimiters
- Descriptive name that indicates the value type
## EXAMPLE_SECRET Marker
**Marker string:** `EXAMPLE_SECRET:`
**Purpose:** Allow intentional secret-like examples in documentation
**Usage rules:**
- Must appear on the SAME LINE as the secret-like pattern
- Marker must be exact (case-sensitive, includes colon)
- Only use for documentation examples, not real values
**Example:**
```bash
# This line will pass CI:
curl -H "Authorization: Bearer demo_token_abc123" EXAMPLE_SECRET: https://api.example.com
```
## Portability and Reuse
**Framework propagation:**
1. **Copy method** (recommended for simplicity):
    - Copy `checks/` and `automation/` from framework to new project
    - Extend patterns as needed
    - Independent updates per project
1. **Git submodule method** (recommended for consistency):
    - Add framework repo as submodule
    - Reference scripts from submodule
    - Update submodule to pull framework changes
    - Still copy `automation/redaction_patterns.txt` locally to extend
**Do NOT use symlinks** (GitHub Actions doesn't reliably support them).
**Child page:** Contract Templates (Framework)
**Status:** [Mirrored to GitHub]
**GitHub Path:** `framework/templates/`
---
## Overview
Reusable templates for starting new documentation mirror projects.
## [CONTRACT.template.md](http://contract.template.md/)
**Purpose:** Root governance contract for a project  
**GitHub Path:** `framework/templates/`[`CONTRACT.template.md`](http://contract.template.md/)  
**Destination:** [`CONTRACT.md`](http://contract.md/) in new project repo root  
### Template
```markdown
# CONTRACT: [PROJECT_NAME]

## Purpose

[One paragraph: what this project does and why it exists]

## Scope

**In scope:**
- [Item 1]
- [Item 2]
- [Item 3]

**Out of scope:**
- [Item 1]
- [Item 2]

## Canonicality

- Notion is the managed Source of Truth for content and planning
- GitHub repo ([owner/repo-name]) is the public mirror and enforcement boundary
- No content is considered published until mirrored to GitHub and passes CI

## Governance

See `contracts/spec.yaml` for:
- Mirror scope and publish rules
- Invariants and validation checks
- Placeholder format standards
- CI enforcement rules

## Key Artifacts

- **Contracts:** `contracts/` directory
- **Protocols:** `protocols/` directory
- **Phases:** `phases/` directory (if applicable)
- **Changelog:** `changelog/` directory

## Workflow

1. All content originates in Notion
2. Export to dev branch
3. Create PR (dev → main)
4. CI validation (`scan-secrets` required)
5. Merge to main = publication
6. Record in Public Drift Log

## Contact

**Maintainer:** [Name]  
**Notion Workspace:** [Workspace Name]  
**Questions:** [Contact method]
```
## spec.template.yaml
**Purpose:** Mirror governance specification  
**GitHub Path:** `framework/templates/spec.template.yaml`  
**Destination:** `contracts/spec.yaml` in new project  
### Template
```yaml
version: "1.0"
project: "[PROJECT_NAME]"
updated: "YYYY-MM-DD"

publish_scope:
  included_paths:
    - "/contracts/"
    - "/protocols/"
    - "/phases/"
    - "/changelog/"
    - "CONTRACT.md"
    - "README.md"
  
  excluded_paths:
    - "/internal/"
    - "/scratch/"
    - "**/DRAFT_*.md"

placeholder_format:
  pattern: "<<[A-Z_]+>>"
  examples:
    - "<<API_KEY>>"
    - "<<WEBHOOK_URL>>"
    - "<<DATABASE_CONNECTION>>"

example_secret_marker:
  marker: "EXAMPLE_SECRET:"
  rule: "Must appear on same line as secret-like pattern"
  enforcement: "CI scan ignores lines with this marker"

invariants:
  - id: "inv_no_real_secrets"
    description: "No real secrets in mirrored content"
    enforcement: "CI scan-secrets check"
  
  - id: "inv_placeholder_format"
    description: "All placeholders use <<FORMAT>>"
    enforcement: "Manual review"
  
  - id: "inv_changelog_directory"
    description: "Changelog is a directory, not CHANGELOG.md"
    enforcement: "Repo structure convention"

ci_checks:
  required:
    - name: "scan-secrets"
      script: "checks/scan_secrets.sh"
      patterns_file: "automation/redaction_patterns.txt"
      blocks_merge: true

workflow:
  branch_strategy: "dev → PR → main"
  branch_protection:
    - "Require PR before merge"
    - "Require scan-secrets check pass"
    - "Require up-to-date branch"
```
## AI_[COLLABORATION.template.md](http://collaboration.template.md/)
**Purpose:** Operating rules for AI agents  
**GitHub Path:** `framework/templates/AI_`[`COLLABORATION.template.md`](http://collaboration.template.md/)  
**Destination:** `contracts/AI_`[`COLLABORATION.md`](http://collaboration.md/) in new project  
### Template
```markdown
# AI Collaboration Contract

## Purpose

This document defines how AI agents should interact with this repository.

## Branch Naming

AI-suggested changes use format:

```
agent/<agent-name>-<topic>
```javascript

**Examples:**
- `agent/claude-fix-typos`
- `agent/notion-ai-update-protocol`
- `agent/chatgpt-add-examples`

## Change Workflow

1. AI proposes changes in agent branch
2. Human reviews proposed changes
3. Human creates PR (agent branch → dev)
4. CI validation runs
5. If passing, human merges dev → main

**Rule:** AIs never merge directly to main.

## Validation Steps

Before proposing changes, AI must:

- [ ] Verify changes align with `contracts/spec.yaml`
- [ ] Replace sensitive values with `<<PLACEHOLDER>>`
- [ ] Add `EXAMPLE_SECRET:` marker to intentional examples
- [ ] Test locally if possible: `bash checks/scan_secrets.sh`
- [ ] Provide clear commit message

## Safety Rules

**AIs must NOT:**
- Commit real secrets, tokens, or credentials
- Modify CI validation scripts without explicit human approval
- Change `automation/redaction_patterns.txt` without human review
- Merge branches (human-only operation)
- Delete content without human confirmation

**AIs should:**
- Ask clarifying questions before major changes
- Propose changes incrementally
- Document reasoning in commit messages
- Flag ambiguities or conflicts

## Communication Style

- Be explicit about what files will change
- Provide before/after diffs when helpful
- Explain reasoning for structural changes
- Highlight breaking changes or dependencies

## Emergency Stop

If AI detects:
- Potential secret exposure
- Contract violation
- Breaking change to governance

**Action:** Stop, alert human, wait for guidance.
```
## routes.template.yaml
**Purpose:** Routing schema (if project uses classification/routing)  
**GitHub Path:** `framework/templates/routes.template.yaml`  
**Destination:** `contracts/routes.yaml` in new project  
### Template
```yaml
version: "1.0"
project: "[PROJECT_NAME]"
updated: "YYYY-MM-DD"

route_prefixes:
  # Define project-specific routing prefixes here
  # Example from Brain Stem:
  
  # PRO:
  #   confidence_threshold: 1.0
  #   extraction_only: true
  #   description: "Project extraction"
  
  # BD:
  #   confidence_threshold: 0.0
  #   classification: true
  #   description: "Brain dump classification"

auto_file_threshold: 0.60

routing_rules:
  # Define how content is classified and routed
  # Customize per project needs
```
## Usage
See **Framework Bootstrap Guide** for step-by-step instructions on using these templates to create a new project.
**Child page:** Framework Bootstrap Guide (Framework)
**Status:** [Mirrored to GitHub]
**GitHub Path:** `framework/BOOTSTRAP_`[`GUIDE.md`](http://guide.md/)
---
## Purpose
Step-by-step guide to create a new documentation mirror project using this framework.
## Prerequisites
- [ ] Notion workspace with content to mirror
- [ ] GitHub account with repo creation permissions
- [ ] Git installed locally
- [ ] Text editor or IDE (VS Code recommended)
- [ ] Basic familiarity with GitHub workflows
## Recommended Approach
**Use separate repos per project:**
- Cleaner access control
- Independent CI/CD
- Flexible public/private settings per project
- Framework updates don't trigger all project rebuilds
## Step 1: Create Notion Project Structure
### In Notion Workspace
1. Under "📁 Projects", create new page: **[Project Name]**
1. Create child pages:
    - **CONTRACT ([Project Name])**
    - **[Project Name] Contracts** (folder)
    - **[Project Name] Protocols** (folder)
    - **[Project Name] Build Phases** (folder, if applicable)
    - **[Project Name] Changelog** (folder)
    - **Drift Log** (operational, Notion-only)
1. Add mirror status properties to each page:
    - **Status:** `[Mirrored to GitHub]` or `[Notion-only]`
    - **GitHub Path:** (if mirrored)
    - **Last Mirror Date:** (if mirrored)
## Step 2: Create GitHub Repository
### On GitHub
1. Create new repo: `[owner]/[project-name]-docs`
1. Settings:
    - [x] Public (recommended for mirror transparency)
    - [x] Initialize with README
    - [ ] Add .gitignore (create manually later)
1. Clone locally:
```bash
git clone https://github.com/[owner]/[project-name]-docs.git
cd [project-name]-docs
```
## Step 3: Copy Framework Files
### Option A: Direct Copy (Simpler)
```bash
# From framework repo or existing project
cp -r [framework-source]/checks ./
cp -r [framework-source]/automation ./
cp -r [framework-source]/.github ./
```
### Option B: Git Submodule (More Maintainable)
```bash
# Add framework as submodule
git submodule add https://github.com/[owner]/docs-mirror-framework.git framework

# Copy required files
cp framework/checks/scan_secrets.sh checks/scan_secrets.sh
cp framework/automation/redaction_patterns.txt automation/redaction_patterns.txt
cp framework/.github/workflows/validate.yml .github/workflows/validate.yml
```
**Note:** Do NOT use symlinks (GitHub Actions portability issue).
## Step 4: Create Repo Structure
```bash
mkdir -p contracts protocols phases changelog checks automation .github/workflows
```
## Step 5: Populate from Templates
### Copy and customize templates:
```bash
# Root contract
cp [framework]/templates/CONTRACT.template.md CONTRACT.md
# Edit: Replace [PROJECT_NAME] with your project name

# Governance spec
cp [framework]/templates/spec.template.yaml contracts/spec.yaml
# Edit: Update project name, scope, invariants

# AI collaboration rules
cp [framework]/templates/AI_COLLABORATION.template.md contracts/AI_COLLABORATION.md
# Edit: Add project-specific rules if needed

# Routes (if needed)
cp [framework]/templates/routes.template.yaml contracts/routes.yaml
# Edit: Define project-specific routing logic
```
### Create [README.md](http://readme.md/):
```markdown
# [Project Name] Documentation

Public mirror of [Project Name] documentation from Notion.

## Purpose

[Brief description]

## Structure

- `CONTRACT.md` - Root governance contract
- `contracts/` - Governance and schema definitions
- `protocols/` - Operating procedures
- `phases/` - Build phase documentation (if applicable)
- `changelog/` - Change log entries
- `DRIFT_LOG.md` - Public mirror sync record

## Workflow

Notion (Source of Truth) → dev → PR → main (Published)

## CI Checks

- `scan-secrets` - Prevents secret exposure (required)

See `contracts/spec.yaml` for full governance rules.
```
## Step 6: Create Public Drift Log
```bash
# Copy template
cp [framework]/templates/DRIFT_LOG.template.md DRIFT_LOG.md
```
Or create manually using template from **Public Drift Log (Framework)** page.
## Step 7: Initialize Git Workflow
```bash
# Create dev branch
git checkout -b dev

# Add initial files
git add .
git commit -m "Initial project structure from framework"
git push -u origin dev

# Create initial PR
# Go to GitHub and create PR: dev → main
# Title: "Initial project setup"
```
## Step 8: Configure Branch Protection
### On GitHub (Settings → Branches → Add rule)
**Branch name pattern:** `main`
**Settings:**
- [x] Require pull request before merging
- [x] Require status checks to pass before merging
- [x] Require branches to be up to date before merging
- [x] Status checks required: `scan-secrets`
## Step 9: Test CI
### Verify secret scan works:
```bash
# Should pass:
echo "Safe content" > test.md
git add test.md
git commit -m "Test CI pass"
git push

# Should fail:
echo "xoxb-secret-token" > test.md
git add test.md
git commit -m "Test CI fail"
git push
# (Then revert this commit)

# Should pass with marker:
echo "xoxb-example-token EXAMPLE_SECRET: in docs" > test.md
git add test.md
git commit -m "Test EXAMPLE_SECRET marker"
git push
```
## Step 10: First Content Mirror
### Export from Notion:
1. Open Notion page to mirror
1. Export as Markdown
1. Place in appropriate directory
1. Replace sensitive values with `<<PLACEHOLDERS>>`
1. Add `EXAMPLE_SECRET:` markers to examples
### Commit and merge:
```bash
git add [files]
git commit -m "[Descriptive message]"
git push

# Create PR on GitHub
# Verify CI passes
# Merge PR
```
### Record in Public Drift Log:
Add entry to `DRIFT_`[`LOG.md`](http://log.md/) following template format.
## Step 11: Update Notion Tracking
1. Mark mirrored pages with:
    - **Status:** `[Mirrored to GitHub]`
    - **GitHub Path:** (exact repo path)
    - **Last Mirror Date:** (today)
1. Add entry to operational Drift Log in Notion
1. Update "Currently Published" tracker (if using)
## Checklist: New Project Setup Complete
- [ ] Notion project structure created
- [ ] GitHub repo created and cloned
- [ ] Framework files copied (checks, automation, workflows)
- [ ] Repo directory structure created
- [ ] Templates customized (CONTRACT, spec.yaml, AI_COLLABORATION)
- [ ] [README.md](http://readme.md/) created
- [ ] Public Drift Log initialized
- [ ] Dev branch created
- [ ] Initial PR merged to main
- [ ] Branch protection enabled
- [ ] CI validation tested (pass, fail, EXAMPLE_SECRET)
- [ ] First content mirrored
- [ ] First Public Drift Log entry added
- [ ] Notion pages marked with mirror status
## Ongoing Operations
See:
- **Drift Control Procedure (Framework)** for mirror sync workflow
- **Mirror Publishing Rules (Framework)** for governance
- **CI Checks Documentation (Framework)** for troubleshooting
**Child page:** contracts/routes.yaml
```yaml
version: "0.1.0"
project: "brainstem-docs"

thresholds:
  auto_file_confidence_min: 0.60

routes:
  - prefix: "PRO:"
    destination: "projects"
    llm_mode: "extract_only"
    rule: "always_file"
    implementation_state: "planned"

  - prefix: "BD:"
    destination: "llm_classified"
    llm_mode: "classify"
    rule: "confidence_based"
    implementation_state: "planned"

  - prefix: "CAL:"
    destination: "events"
    llm_mode: "extract"
    rule: "planned"
    implementation_state: "planned"

  - prefix: "R:"
    destination: "research_jobs"
    llm_mode: "planned"
    rule: "planned"
    implementation_state: "planned"

  - prefix: "fix:"
    destination: "corrections"
    llm_mode: "planned"
    rule: "planned"
    implementation_state: "planned"

data_contracts:
  tables_required:
    - "People"
    - "Projects"
    - "Ideas"
    - "Admin"
    - "Events"
    - "Inbox Log"

invariants:
  - id: "no_secrets_in_repo"
    severity: "high"
    description: "Repo must not contain credentials, tokens, webhook URLs, or private keys."
  - id: "placeholders_only"
    severity: "high"
    description: "Sensitive values must be represented as <<ALL_CAPS_WITH_UNDERSCORES>>."
```
**Child page:** README.md
# Brain Stem Docs (Public Mirror)
This repository is a **public, sanitized Markdown mirror** of Brain Stem documentation authored in Notion.
## Rules
- Public repo = **no secrets, no inbound webhook URLs, no personal identifiers**
- Use placeholders only: `<<LIKE_THIS>>`
- Run the pre-commit checklist in `protocols/`[`SECURITY.md`](http://security.md/) before every commit
## Structure
- [`CONTRACT.md`](http://contract.md/) — blueprint (what must be true)
- `contracts/spec.yaml` — machine-readable anchors
- `phases/` — procedural build steps (how to implement)
- `protocols/` — publishing + security rules
- `checks/` — validation scripts/specs (public-safe)
- `automation/` — redaction patterns and automation notes
- `reports/` — QA outputs and audit notes
- `examples/` — sanitized examples
- `changelog/` — change history (public-safe)
## Notion Source
- Notion workspace/page: `<<NOTION_SOURCE_URL_OR_ID>>`
**Child page:** contracts/AI_COLLABORATION.md
# AI Collaboration Contract (Brainstem Docs)
This repo is a public mirror. Any agent (ChatGPT, Claude, Notion AI, scripts) MUST follow these rules when producing or editing content that may be published here.
## Scope
- This contract applies to all content in publish scope:
    - [CONTRACT.md](http://contract.md/), [README.md](http://readme.md/)
    - contracts/, protocols/, phases/, checks/, automation/, changelog/, reports/
## Non-negotiable invariants
1. **No secrets in public mirror**
- Never include real credentials, API keys, tokens, private keys, session cookies, or real webhook URLs.
1. **Placeholders only**
- Any sensitive value must be represented as a placeholder:
    - Format: `<<ALL_CAPS_WITH_UNDERSCORES>>`
    - Examples: `<<NOTION_TOKEN>>`, `<<MAKE_WEBHOOK_URL>>`, `<<SLACK_BOT_TOKEN>>`
1. **Examples must be marked**
- If documentation needs to show secret-like example strings (e.g., token prefixes, key headers, webhook domains), the line MUST be prefixed with:
    - `EXAMPLE_SECRET:`
- CI secret scanning ignores lines containing `EXAMPLE_SECRET:`. Unmarked secret-like strings will fail CI.
## How agents should propose changes
- Prefer small, reviewable diffs.
- Do not rename/move files without updating references in docs and contracts.
- If CI fails, first fix the smallest change that makes CI green (do not widen exclusions unless necessary).
## Definition of “publish safe”
A change is publish safe if:
- It stays inside publish scope
- It introduces no real secrets
- Any secret-like example strings are explicitly marked with `EXAMPLE_SECRET:`
- `checks/scan_secrets.sh` passes on PR
---
## Hybrid governance (Notion home base, Git integration point)
This system operates as a hybrid:
- **Notion is the home base** for planning, drafting, and database-managed knowledge.
- **GitHub is the integration point** for external agents/models and the canonical **published bytes** for the public mirror.
### Two lanes
**Lane A — Notion → Git (normal publishing lane)**
- Humans and Notion-native AI edit in Notion.
- When a doc is ready to publish, export/render it into the repo at the exact mirror path.
- Changes land via PR to `dev` and merge to `main` only when CI passes.
**Lane B — Git → Notion (agent/automation lane)**
- External agents/models propose changes only via PRs to `dev`.
- After merge to `main`, the corresponding Notion page must be updated (manually for now; automated later).
- If a Git change was made without Notion backfill, that is **drift** and must be reconciled.
### Source-of-truth by artifact type
- **Planning, tasks, database fields, and drafts:** Notion is canonical.
- **Public mirror published documents in publish scope:** GitHub `main` is canonical bytes.
- **CI behavior and security enforcement:** repo scripts + CI are canonical.
### Drift definition
Drift exists when:
- A publish-scope file in GitHub does not match its Notion source page, or
- A publish-scope file exists in GitHub with no Notion source page, or
- A Notion page claims a mirror path that does not exist in the repo.
### Resolution rule (when they disagree)
1. For **planning/drafts**: Notion wins.
1. For **published mirror bytes and CI behavior**: GitHub `main` wins.
1. Always document reconciliation in the operational drift log (Notion) when it occurs.

10 child pages covering mirror publishing rules, drift control, CI checks, automation config, contract templates, bootstrap guide, and protocol files. Written for the full automated system — pick up when MVP is proven.

**Child page:** 📁 Projects
**Child page:** 🧠 Brain Stem Project → Mirror Mapping
**Purpose:** Maps Brain Stem Notion pages to their intended GitHub mirror paths in `sharedterrain/brainstem-docs`.
**Status Legend:**
- ✅ **Exists** = Already in repo (per snapshot)
- 🟡 **Needs Export** = Notion page exists, not yet mirrored
- 🔴 **Missing Source** = Repo file exists but no clear Notion source
- ⚪ **Planned** = Future content, not yet created
---
## Mapping Table
| **Notion Page** | **GitHub Path** | **Status** | **Notes** |
| --- | --- | --- | --- |
| **Root Files** |  |  |  |
| [Untitled](https://www.notion.so/cb5393105c784cc3969571a898b4f81e) | [`CONTRACT.md`](http://contract.md/) | ✅ Exists | 892 bytes, Feb 4 |
| (None — needs creation) | [`README.md`](http://readme.md/) | ✅ Exists | 891 bytes, Feb 4 — create Notion doc source |
| **Contracts** |  |  |  |
| [Untitled](https://www.notion.so/98d781fe40ed4e31a566f0d8886325fc) | `contracts/spec.yaml` | ✅ Exists | 2201 bytes, Feb 5 20:54 |
| (None — part of spec page) | `contracts/routes.yaml` | ✅ Exists | 1164 bytes, Feb 5 20:35 — split from spec, needs Notion update |
| (None — needs creation) | `contracts/AI_`[`COLLABORATION.md`](http://collaboration.md/) | ✅ Exists | 1585 bytes, Feb 5 20:54 — create Notion source |
| **Protocols** |  |  |  |
| [Untitled](https://www.notion.so/3acc8d331e8d4ace8f2908561ee84cd4) | `protocols/`[`PUBLISHING.md`](http://publishing.md/) | ✅ Exists | 944 bytes, Feb 4 |
| [Untitled](https://www.notion.so/ce67745f4da14ae183d196c44c527e92) | `protocols/`[`SECURITY.md`](http://security.md/) | ✅ Exists | 1719 bytes, Feb 5 19:37 |
| [Untitled](https://www.notion.so/dd011d8f53f74b8baef58b6211b2a8c6) | `protocols/CHANGE_`[`CONTROL.md`](http://control.md/) | 🟡 Needs Export | Notion page exists, not in repo yet |
| [Untitled](https://www.notion.so/8efaa207156647ca921ede78c7fb32b9) | `protocols/`[`MIRRORING.md`](http://mirroring.md/) | 🟡 Needs Export | Notion page exists, not in repo yet |
| [Untitled](https://www.notion.so/8d45305a868d4e73a6555b9e96d53a18) | `protocols/`[`OPERATING.md`](http://operating.md/) | 🟡 Needs Export | Notion page exists, not in repo yet |
| **Phases** |  |  |  |
| [Untitled](https://www.notion.so/ed998ca8e6464de188987fbf06e30568) | `phases/phase_0_`[`setup.md`](http://setup.md/) | 🟡 Needs Export | Repo has `phases/` dir, content not yet exported |
| [Untitled](https://www.notion.so/0538979e023a46528fb1a70b60ccd4ef) | `phases/phase_1_`[`capture.md`](http://capture.md/) | 🟡 Needs Export | Notion page exists, not in repo yet |
| [Untitled](https://www.notion.so/548d362076b243f1ad33df72fd6617a1) | `phases/phase_2_`[`classification.md`](http://classification.md/) | 🟡 Needs Export | Notion page exists, not in repo yet |
| [Untitled](https://www.notion.so/33c94ae1c521433ea32092a1a7856f90) | `phases/phase_3_`[`research.md`](http://research.md/) | ⚪ Planned | Defer until Phase 3 active |
| [Untitled](https://www.notion.so/25f0383da86e40c5ab833bf28f7185ad) | `phases/phase_4_`[`synthesis.md`](http://synthesis.md/) | ⚪ Planned | Defer until Phase 4 active |
| [Untitled](https://www.notion.so/7c7e53e60fd5419aa4c129bdcf0d2432) | `phases/phase_5_`[`publishing.md`](http://publishing.md/) | ⚪ Planned | Defer until Phase 5 active |
| Phases 6–9 | `phases/phase_[6-9]_*.md` | ⚪ Planned | Defer until phases active |
| **CI & Automation** |  |  |  |
| (Documented in framework) | `checks/scan_`[`secrets.sh`](http://secrets.sh/) | ✅ Exists | 1658 bytes, Feb 5 19:37 — executable script |
| (Documented in framework) | `automation/redaction_patterns.txt` | ✅ Exists | 364 bytes, Feb 5 20:36 |
| **Changelog** |  |  |  |
| [Untitled](https://www.notion.so/1d9d1c1b34c847e980ced47ec4e82421) | `changelog/` | 🟡 Needs Export | Directory exists (empty), needs entries from Notion |
| **Reports** |  |  |  |
| (None yet) | `reports/` | ⚪ Planned | Directory exists (empty), content TBD |
| **Examples** |  |  |  |
| (None — not in publish scope) | `examples/` | 🔴 Orphan | Exists in repo but NOT in publish_scope — remove or add to scope |
| **Drift Control** |  |  |  |
| (Framework: Public Drift Log) | `DRIFT_`[`LOG.md`](http://log.md/) | 🟡 Needs Creation | Use framework template, initialize empty log |
---
## Summary
**Already Mirrored (6 files):**
- [`CONTRACT.md`](http://contract.md/)
- [`README.md`](http://readme.md/) (no Notion source)
- `contracts/spec.yaml`
- `contracts/routes.yaml` (needs Notion sync)
- `contracts/AI_`[`COLLABORATION.md`](http://collaboration.md/) (no Notion source)
- `protocols/`[`PUBLISHING.md`](http://publishing.md/)
- `protocols/`[`SECURITY.md`](http://security.md/)
- `checks/scan_`[`secrets.sh`](http://secrets.sh/)
- `automation/redaction_patterns.txt`
**Priority Exports (Stage 2):**
1. `contracts/routes.yaml` — reconcile Notion spec page to reflect split
1. `protocols/CHANGE_`[`CONTROL.md`](http://control.md/)
1. `protocols/`[`MIRRORING.md`](http://mirroring.md/)
1. `protocols/`[`OPERATING.md`](http://operating.md/)
1. `phases/phase_0_`[`setup.md`](http://setup.md/)
1. `phases/phase_1_`[`capture.md`](http://capture.md/)
1. `phases/phase_2_`[`classification.md`](http://classification.md/)
**Create Notion Source Pages:**
- README mirror page (document repo purpose)
- AI_COLLABORATION mirror page (document agent rules)
**Repo Cleanup:**
- `examples/` directory — either remove or add to publish_scope in spec.yaml
**Initialize:**
- `DRIFT_`[`LOG.md`](http://log.md/) — use framework template from [Operational Drift Log (Notion-only) (Framework)](https://www.notion.so/5c27b3122e3c473ea46e66847dc2a4d1)
- `changelog/` entries — migrate from [Untitled](https://www.notion.so/1d9d1c1b34c847e980ced47ec4e82421)
---
## Recommended Next Actions
### Immediate (Before Next Mirror Pass)
1. **Update Notion contracts/spec page** to document `routes.yaml` split
1. **Create Notion source pages** for README and AI_COLLABORATION
1. **Add mirror status banners** to all Notion pages:
```javascript
**Status:** [Mirrored to GitHub] or [Notion-only]
**GitHub Path:** `path/to/file.md`
**Last Mirror Date:** YYYY-MM-DD
```
### Stage 2 Mirror Priority
Export in this order (contracts → protocols → phases):
**Batch 1: Contracts**
- Sync contracts/spec page to reflect routes.yaml split
- Export contracts/routes as separate page (if not already split in Notion)
**Batch 2: Protocols**
- CHANGE_[CONTROL.md](http://control.md/)
- [MIRRORING.md](http://mirroring.md/)
- [OPERATING.md](http://operating.md/) (from Operating Protocol)
**Batch 3: Phases**
- phase_0_[setup.md](http://setup.md/)
- phase_1_[capture.md](http://capture.md/)
- phase_2_[classification.md](http://classification.md/)
**Batch 4: Public Drift Log**
- Initialize DRIFT_[LOG.md](http://log.md/) with first entries documenting Stage 1 mirror
### Notion Organization Adjustment
Consider moving Brain Stem pages under **📁 Projects** in the new framework structure:
- Current: Brain Stem Project (workspace root)
- Proposed: 🏠 Documentation Mirror System → 📁 Projects → 🧠 Brain Stem Project
This makes it clear Brain Stem is one instance of the reusable framework.
**Defer this move** until first mirror pass succeeds to avoid breaking references.
**Child page:** Brain Stem Project
## GitHub Source
[https://github.com/sharedterrain/brainstem-docs](https://github.com/sharedterrain/brainstem-docs)
## Project File Map
- contracts/
- protocols/
- phases/
- reports/
- [CONTRACT.md](http://contract.md/)
- [README.md](http://readme.md/)
**Rule:** This project repo must never contain framework-only docs.
**Child page:** protocols/CHANGE_CONTROL.md
# Change Control Protocol
## Purpose
Define how changes flow between Notion (canonical source) and GitHub (public mirror + enforcement gate) while preventing drift and maintaining publish safety.
## Scope
Applies to all content in mirror publish scope:
- `CONTRACT.md`, `README.md`
- `contracts/`, `protocols/`, `phases/`
- `checks/`, `automation/`, `changelog/`, `reports/`
## Definitions
- **Canonical source**: Notion workspace (managed content and planning)
- **Enforcement gate**: GitHub CI (scan-secrets must pass)
- **Published**: Content merged to `main` branch in GitHub repo
- **Drift**: Mismatch between Notion content and GitHub mirror
- **Publish-safe**: No real secrets, placeholders only, CI passes
## Normal Flow (Notion → Export → Repo → PR)
**This is the default path for all changes.**
1. **Edit in Notion**
    - Update canonical Notion page
    - Mark page status: `[Mirrored to GitHub]`
    - Document GitHub path: `path/to/file.md`
1. **Pre-export checks**
    - [ ] Replace sensitive values with `<<ALL_CAPS_WITH_UNDERSCORES>>`
    - [ ] Add `EXAMPLE_SECRET:` marker to any secret-like examples
    - [ ] Verify content matches governance in `contracts/spec.yaml`
1. **Export**
    - Export Notion page as Markdown
    - Place in correct repo directory
    - Verify filename matches GitHub path documented in Notion
1. **Commit to dev branch**
```bash
git checkout dev
git add [files]
git commit -m "[descriptive message]"
git push origin dev
```
1. **Create PR (dev → main)**
    - Create pull request on GitHub
    - Wait for CI checks to complete
    - **Do not merge if **`scan-secrets`** fails**
1. **Merge**
    - Merge PR after CI passes
    - Content is now **published**
1. **Record**
    - [ ] Add entry to operational Drift Log (Notion)
    - [ ] Update "Last Mirror Date" in Notion page
    - [ ] Update "Currently Published" tracker
## Exception Flow (GitHub-First Hotfix → Backfill Notion)
**Use only for urgent CI fixes or repo-breaking issues.**
1. **Hotfix in repo**
    - Fix directly in `dev` branch or hotfix branch
    - Create PR, verify CI passes
    - Merge to `main`
1. **Backfill to Notion (within 24 hours)**
    - Update corresponding Notion page to match repo
    - Add note: `[Backfilled from GitHub hotfix YYYY-MM-DD]`
    - Record in operational Drift Log with explanation
1. **Prevent recurrence**
    - Document why hotfix was needed
    - Update pre-export checklist if applicable
## Review Checklist
**Before every commit to dev:**
- [ ] No real credentials, API keys, tokens, or webhook URLs
- [ ] All sensitive values use `<<ALL_CAPS_WITH_UNDERSCORES>>`
- [ ] Secret-like examples prefixed with `EXAMPLE_SECRET:` on same line
- [ ] Content stays inside publish scope paths
- [ ] Filenames match Notion → GitHub path mapping
- [ ] File paths use correct conventions:
    - `checks/scan_secrets.sh`
    - `automation/redaction_patterns.txt`
    - `contracts/spec.yaml`, `contracts/routes.yaml`
    - `contracts/AI_COLLABORATION.md`
    - `changelog/` (directory, not `CHANGELOG.md`)
**Before merging PR:**
- [ ] CI check `scan-secrets` passes
- [ ] PR description references Notion source page
- [ ] Changes reviewed for publish safety
**After merge:**
- [ ] Public Drift Log entry added
- [ ] Notion page updated with latest mirror date
- [ ] Operational Drift Log entry added
## What Counts as Drift
**Drift exists when:**
- Notion page content differs from corresponding GitHub file
- GitHub file exists but no Notion source page (orphan)
- Notion page marked `[Mirrored to GitHub]` but file missing from repo
- Notion page "GitHub Path" doesn't match actual repo structure
- "Last Mirror Date" in Notion older than actual file update in repo
- Public Drift Log missing entry for a merged PR
**Resolution priority:**
1. **For content/planning**: Notion wins (update repo from Notion)
1. **For CI behavior**: Repo wins (update Notion to document actual behavior)
1. **For sync conflicts**: Compare timestamps, use most recent, document reconciliation
**Drift detection cadence:**
- Manual review: monthly or after major mirror operations
- Automated check: (planned future enhancement)
- Ad-hoc: whenever uncertainty about Notion ↔ GitHub alignment
## Emergency Contacts
- **Maintainer**: `<<MAINTAINER_NAME>>`
- **Notion workspace**: `<<NOTION_WORKSPACE_ID>>`
- **GitHub repo**: `sharedterrain/brainstem-docs`
**Child page:** phases/phase_0_setup.md
# Phase 0: Setup & Configuration
## Objective
Establish and validate the Notion → GitHub mirror system for `sharedterrain/brainstem-docs`, ensuring CI gates work and Notion source pages are ready for Stage 2 exports.
## Preconditions
- [ ] GitHub account with access to `sharedterrain/brainstem-docs`
- [ ] Git installed locally
- [ ] Text editor (VS Code recommended)
- [ ] Bash shell (macOS/Linux/WSL)
- [ ] Notion workspace access with export permissions
## Repo Setup
### Clone Repository
```bash
# Clone repo
git clone https://github.com/sharedterrain/brainstem-docs.git
cd brainstem-docs

# Verify remote
git remote -v
```
### Checkout Dev Branch
```bash
# Switch to dev branch
git checkout dev

# Pull latest
git pull origin dev

# Verify current branch
git branch
```
## Verify Publish-Scope Tree
**Check that these paths exist:**
```bash
# List publish-scope directories
ls -la
ls -la contracts/
ls -la protocols/
ls -la phases/
ls -la checks/
ls -la automation/
ls -la changelog/
ls -la reports/
```
**Expected structure:**
```javascript
brainstem-docs/
├── CONTRACT.md
├── README.md
├── contracts/
│   ├── spec.yaml
│   ├── routes.yaml
│   └── AI_COLLABORATION.md
├── protocols/
│   ├── SECURITY.md
│   ├── PUBLISHING.md
│   ├── CHANGE_CONTROL.md
│   ├── MIRRORING.md
│   └── OPERATING.md
├── phases/
│   └── (phase docs)
├── checks/
│   └── scan_secrets.sh
├── automation/
│   └── redaction_patterns.txt
├── changelog/
│   └── (changelog entries)
└── reports/
    └── (QA reports)
```
**Verify exclusions:**
```bash
# examples/ should NOT exist or should be in .gitignore
ls -la examples/ 2>/dev/null || echo "examples/ correctly excluded"
```
## Run Local Checks
### Validate Secret Scan
```bash
# Run secret scan on current content
bash checks/scan_secrets.sh
```
**Expected output:**
```javascript
🔍 Scanning for secrets in public mirror scope...
✅ No secrets found in publish scope
```
**If scan fails:**
- Review pattern file:
```bash
cat automation/redaction_patterns.txt
```
- Check for real secrets in code
- Verify `EXAMPLE_SECRET:` markers on example lines
### Verify Pattern File
```bash
# Review current patterns
cat automation/redaction_patterns.txt
```
**Should include patterns for:**
- EXAMPLE_SECRET: Slack tokens (`xoxb-`, `xoxp-`)
- EXAMPLE_SECRET: Webhook URLs ([`hook.make.com`](http://hook.make.com/), [`https://hook`](https://hook/))
- EXAMPLE_SECRET: API keys (`sk-ant-`, `Authorization: Bearer`)
- EXAMPLE_SECRET: Airtable patterns ([`api.airtable.com/v0/app`](http://api.airtable.com/v0/app))
- EXAMPLE_SECRET: Generic secrets (`secret_`, `BEGIN PRIVATE KEY`)
## Notion Source Pages Required
**Under 🏠 Documentation Mirror System, verify these pages exist:**
### Already Created (Stage 1)
- [ ] `README.md`
- [ ] `contracts/routes.yaml`
- [ ] `contracts/AI_COLLABORATION.md`
### Stage 2 Protocol Pages
- [ ] `protocols/CHANGE_CONTROL.md`
- [ ] `protocols/MIRRORING.md`
- [ ] `protocols/OPERATING.md`
### Stage 2 Phase Pages
- [ ] `phases/phase_0_setup.md` (this page)
- [ ] Additional phase pages as needed
**Each page must have:**
- Title matching exact repo path
- Mirror status banner: `[Mirrored to GitHub]` or `[Notion-only]`
- GitHub path documented if mirrored
- No real secrets, placeholders only:`<<ALL_CAPS_WITH_UNDERSCORES>>`
- Secret examples marked with `EXAMPLE_SECRET:` on same line
## Export + Copy Procedure
### Export from Notion
1. **Select page to mirror**
1. **Click ⋯ menu → Export**
    - Format: Markdown & CSV
    - Include subpages: No
1. **Download and unzip**
1. **Sanitize if needed** (strip linkified filenames)
### Copy to Repo
**Example for protocols:**
```bash
# Assuming exported files in ~/Downloads/Export-*/
cd ~/code/brainstem-docs
git checkout dev

# Copy protocol files
cp ~/Downloads/Export-*/CHANGE_CONTROL.md ./protocols/CHANGE_CONTROL.md
cp ~/Downloads/Export-*/MIRRORING.md ./protocols/MIRRORING.md
cp ~/Downloads/Export-*/OPERATING.md ./protocols/OPERATING.md

# Copy phase files
cp ~/Downloads/Export-*/phase_0_setup.md ./phases/phase_0_setup.md

# Verify placement
ls -la protocols/
ls -la phases/
```
### Validate Before Commit
```bash
# Run secret scan
bash checks/scan_secrets.sh

# Review changes
git status
git diff
```
## PR Procedure (dev → main)
### Commit Changes
```bash
# Stage files
git add protocols/ phases/

# Commit with descriptive message
git commit -m "docs: Phase 0 mirror - add protocols and phase docs

- Added protocols/CHANGE_CONTROL.md
- Added protocols/MIRRORING.md
- Added protocols/OPERATING.md
- Added phases/phase_0_setup.md

Notion sources:
- 🏠 Documentation Mirror System"

# Push to dev
git push origin dev
```
### Create Pull Request
1. **Navigate to:**
```javascript
https://github.com/sharedterrain/brainstem-docs
```
1. **Create PR:**
    - Base: `main`
    - Compare: `dev`
    - Title: `Phase 0: Mirror protocols and phase docs`
    - Description: Link to Notion pages
1. **Wait for CI:**
    - Status check: `scan-secrets` must pass ✅
1. **Merge PR** when green
### Backfill Notion
```bash
# Pull merged changes
git checkout main
git pull origin main

# Verify in log
git log --oneline -5
```
**Update Notion pages:**
- Add `Last Mirror Date: YYYY-MM-DD` to each mirrored page
- Mark in "Currently Published" tracker
## Exit Criteria
**Phase 0 is complete when:**
- [ ] Local repo cloned and `dev` branch active
- [ ] Publish-scope tree verified (correct directories present)
- [ ] `examples/` excluded from publish scope
- [ ] Secret scan passes locally: `bash checks/scan_secrets.sh`→ ✅
- [ ] Pattern file validated and correct
- [ ] All required Notion source pages exist under 🏠 Documentation Mirror System
- [ ] Stage 1 pages mirrored:
    - `README.md`
    - `contracts/routes.yaml`
    - `contracts/AI_COLLABORATION.md`
- [ ] Stage 2 protocol pages mirrored:
    - `protocols/CHANGE_CONTROL.md`
    - `protocols/MIRRORING.md`
    - `protocols/OPERATING.md`
- [ ] Stage 2 phase page mirrored:
    - `phases/phase_0_setup.md`
- [ ] PR (dev → main) created and merged successfully
- [ ] CI check `scan-secrets` passed on GitHub ✅
- [ ] Notion pages updated with mirror dates
- [ ] Drift Log entries recorded
**Once exit criteria met, Phase 0 is complete.**
## Next Phase
Proceed to Phase 1: Brain Dump Capture (when ready).
## Troubleshooting
**Problem: Secret scan fails**
- Check output for matched pattern and line number
- Replace real secrets with `<<PLACEHOLDER>>`
- Add `EXAMPLE_SECRET:` to intentional examples
- Re-run scan until clean
**Problem: Notion export has linkified filenames**
- If Notion exported linkified filenames, strip link markup so paths are plain text before copying into the repo.
- Or manually edit before copying to repo
- Future prevention: use code blocks in Notion content
**Problem: examples/ directory still in repo**
- Check if in publish scope: `cat contracts/spec.yaml`
- If not in scope, remove:
```bash
git rm -r examples/
git commit -m "chore: remove examples/ from publish scope"
```
- Or add to scope if needed (update spec.yaml first)
**Problem: CI check doesn't run**
- Verify GitHub Actions workflow exists:
```bash
cat .github/workflows/validate.yml
```
- Check repo Settings → Actions → enabled
- Review Actions tab for error logs
**Child page:** protocols/MIRRORING.md
# Mirroring Procedure (Notion → GitHub)
## Purpose
Step-by-step terminal procedure for mirroring Notion documentation to the `sharedterrain/brainstem-docs` public GitHub repo.
## Publish Scope
Only these paths are mirrored:
- `CONTRACT.md`
- `README.md`
- `contracts/`
- `protocols/`
- `phases/`
- `checks/`
- `automation/`
- `changelog/`
- `reports/`
## Preconditions
- [ ] Notion pages marked `[Mirrored to GitHub]`
- [ ] GitHub path documented on each Notion page
- [ ] No real secrets in content (placeholders only: `<<ALL_CAPS_WITH_UNDERSCORES>>`)
- [ ] Secret-like examples prefixed with `EXAMPLE_SECRET:` on same line
- [ ] Local repo clone exists at `~/code/brainstem-docs` (or equivalent)
## Export from Notion
1. **Export page(s)**
    - In Notion, click `⋯` menu → Export
    - Format: **Markdown & CSV**
    - Include subpages: **No** (export each page individually)
    - Download and unzip
1. **Sanitization note**
    - Notion may export `file.md` references as links like `[`[`file.md`](http://file.md/)`](`[`http://file.md`](http://file.md/)`)`
    - Before copying into the repo, strip link markup so it becomes plain text “file.md” (or put file paths inside fenced code blocks in Notion pages to avoid linkification)
## Copy into Repo
```bash
cd ~/code/brainstem-docs
git checkout dev
```
**Target paths (examples):**
```bash
# Root files
cp ~/Downloads/Export-*/README.md ./README.md
cp ~/Downloads/Export-*/CONTRACT.md ./CONTRACT.md

# Contracts (YAML): copy/paste from Notion code blocks into these files, then save
# contracts/spec.yaml
# contracts/routes.yaml
cp ~/Downloads/Export-*/AI_COLLABORATION.md ./contracts/AI_COLLABORATION.md

# Protocols
cp ~/Downloads/Export-*/SECURITY.md ./protocols/SECURITY.md
cp ~/Downloads/Export-*/PUBLISHING.md ./protocols/PUBLISHING.md
cp ~/Downloads/Export-*/CHANGE_CONTROL.md ./protocols/CHANGE_CONTROL.md
cp ~/Downloads/Export-*/MIRRORING.md ./protocols/MIRRORING.md

# Phases
cp ~/Downloads/Export-*/phase_0_setup.md ./phases/phase_0_setup.md
cp ~/Downloads/Export-*/phase_1_capture.md ./phases/phase_1_capture.md
cp ~/Downloads/Export-*/phase_2_classification.md ./phases/phase_2_classification.md

# Changelog entries
cp ~/Downloads/Export-*/2026-02-*.md ./changelog/
```
**Verify file placement:**
```bash
ls -la contracts/ protocols/ phases/ changelog/
```
## Local Validation
**Run secret scan:**
```bash
bash checks/scan_secrets.sh
```
**Expected output:**
```javascript
🔍 Scanning for secrets in public mirror scope...
✅ No secrets found in publish scope
```
**If scan fails:**
1. Check CI output for line number
1. Fix: replace with `<<ALL_CAPS_WITH_UNDERSCORES>>` or add `EXAMPLE_SECRET:` marker
1. Re-run scan until clean
## Commit and PR
```bash
# Stage changes
git add CONTRACT.md README.md contracts/ protocols/ phases/ changelog/

# Commit with descriptive message
git commit -m "docs: mirror [page names] from Notion

- Updated contracts/spec.yaml
- Added protocols/MIRRORING.md
- Exported Phase 0 and Phase 1 docs

Notion sources:
- [list Notion page URLs or titles]"

# Push to dev
git push origin dev
```
**Create PR on GitHub:**
1. Navigate to [`https://github.com/sharedterrain/brainstem-docs`](https://github.com/sharedterrain/brainstem-docs)
1. Create pull request: `dev` → `main`
1. Title: `Mirror sync: [description]`
1. Body: link to Notion source pages
1. Wait for CI check `scan-secrets` to pass ✅
1. Merge PR
## Post-Merge Backfill
**After merge to main:**
```bash
# Pull latest
git checkout main
git pull origin main

# Confirm published
git log --oneline -5
```
**Update Notion:**
- [ ] Mark pages with `Last Mirror Date: YYYY-MM-DD`
- [ ] Add entry to operational Drift Log
- [ ] Update Currently Published tracker
## Exception: Git-First Changes
**If changes made directly in GitHub (hotfix):**
1. Pull latest from `main`
1. Update corresponding Notion pages within 24 hours
1. Add note in Notion: `[Backfilled from GitHub hotfix YYYY-MM-DD]`
1. Document in operational Drift Log with explanation
## Troubleshooting
**CI scan fails:**
- Check pattern file: `automation/redaction_patterns.txt`
- Verify all secrets use `<<ALL_CAPS_WITH_UNDERSCORES>>` format
- Confirm examples have `EXAMPLE_SECRET:` marker on same line
**File not in publish scope:**
- Verify path matches `contracts/spec.yaml` publish_scope definition
- If needed, update spec.yaml first, then re-export
**Notion export contains sensitive data:**
- **STOP** - do not commit
- Return to Notion, replace with placeholder
- Re-export clean version
- Never commit real credentials to public repo
## Quick Reference
```bash
# Standard mirror workflow
cd ~/code/brainstem-docs
git checkout dev
git pull origin dev

# Copy exported files to correct paths
cp [source] [target]

# Validate
bash checks/scan_secrets.sh

# Commit
git add .
git commit -m "docs: mirror [description]"
git push origin dev

# Create PR on GitHub (dev → main)
# Wait for CI, merge

# Backfill Notion with mirror date
```
**Child page:** phases/phase_1_capture.md
# Phase 1: Brain Dump Capture
## Objective
Establish and validate the capture workflow: brain dump → Inbox Log → structured entries. Ensure all capture channels route correctly and Inbox Log maintains audit integrity.
## Inputs
**Brain dumps arrive via:**
- Slack DMs (direct message to Brain Stem bot)
- Slack commands (slash commands in any channel)
- Manual Notion entry (direct to Inbox Log database)
- Email forwarding (future: not implemented in Phase 1)
**Capture requirements:**
- Every input gets an Inbox Log entry (audit backbone)
- Timestamp recorded automatically
- Raw text preserved
- Classification happens post-capture (Phase 2)
## Capture Channels (Quick Entry Points)
### Slack Bot DM
**Setup:**
```javascript
1. DM the Brain Stem bot: <<SLACK_BOT_NAME>>
2. Type brain dump as free-form text
3. Bot acknowledges and logs entry
```
**Example flow:**
```javascript
You: "PRO: Update docs mirror Phase 1 by Friday"
Bot: "✅ Logged to Inbox (#12345)"
```
**Behind the scenes:**
- Slack webhook triggers [Make.com](http://make.com/) scenario
- Make posts to Airtable Inbox Log
- Returns confirmation to Slack
### Slack Slash Command
**Usage:**
```javascript
/braindump [text]
```
**Example:**
```javascript
/braindump BD: Meeting notes from sync with external AI vendor
```
**Result:**
- Entry created in Inbox Log
- Ephemeral confirmation message (only you see it)
- Original message not visible to channel
### Manual Notion Entry
**Direct entry to Inbox Log database:**
1. Open Inbox Log in Notion
1. Click "+ New" or press `Cmd/Ctrl + N`
1. Fill required fields:
    - **Raw Input** (text): The brain dump content
    - **Timestamp** (auto-filled if created via button)
    - **Source** (select): Manual, Slack, Email, etc.
1. Save (creates audit record)
**Use case:**
- Offline brain dumps
- Batch imports from notes
- Corrections or manual logs
## Notion Database Targets
### Inbox Log (Primary)
**Purpose:** Audit backbone for all incoming brain dumps
**Required fields:**
```yaml
- Raw Input: text (long text property)
- Timestamp: date (with time)
- Source: select (Slack, Manual, Email, etc.)
- Status: select (New, Processed, Archived)
- Routing Prefix: text (extracted from Raw Input)
```
**Optional fields (Phase 2):**
```yaml
- Classification Confidence: number (0.00 to 1.00)
- Destination: relation (links to Projects/People/Ideas/etc.)
- Processing Notes: text
```
**Database location:**
```javascript
Notion workspace → Brain Stem Project → Inbox Log
```
### Destination Databases (Phase 2 and beyond)
**Not implemented in Phase 1:**
- Projects
- People
- Ideas
- Admin
- Events
- Research Jobs/Articles/Drafts
**Phase 1 scope:** All entries stay in Inbox Log until Phase 2 classification is implemented.
## Naming Conventions
### Routing Prefixes (Informational Only in Phase 1)
These prefixes help future classification but are not enforced in Phase 1:
**Format:**
```javascript
PREFIX: [content]
```
**Recognized prefixes:**
- `PRO:` – Project-related (confidence 1.0, deterministic destination Projects, extraction-only)
- `BD:` – Brain dump (requires classification)
- `CAL:` – Calendar/event (scaffolded)
- `R:` – Research (scaffolded)
- `fix:` – Correction or update (scaffolded)
**Examples:**
```javascript
PRO: Update mirror docs by Friday
BD: Had interesting conversation about AI governance
CAL: Team sync next Tuesday 2pm
R: Look into Claude routing strategies
fix: Correct webhook URL in config
```
**Phase 1 behavior:**
- Prefix extracted and stored in Inbox Log
- No automatic routing (classification is Phase 2)
- All entries remain in Inbox Log for manual review
### Timestamp Format
**Auto-generated timestamps:**
```javascript
YYYY-MM-DD HH:MM:SS (local timezone)
```
**Example:**
```javascript
2026-02-07 09:30:15
```
## Validation Checklist
### Test Slack Bot Capture
**Steps:**
```javascript
1. DM Brain Stem bot with test message:
   "TEST: Phase 1 capture validation"

2. Verify bot responds:
   "✅ Logged to Inbox (#XXXXX)"

3. Check Inbox Log in Notion:
   - New entry exists
   - Raw Input contains test message
   - Timestamp is current
   - Source = "Slack"
   - Status = "New"
```
### Test Manual Entry
**Steps:**
```javascript
1. Open Inbox Log in Notion

2. Create new entry:
   Raw Input: "TEST: Manual entry validation"
   Source: Manual

3. Verify entry saved:
   - Timestamp auto-filled
   - Status defaults to "New"
```
### Verify Webhook Integration
**Check **[**Make.com**](http://make.com/)** scenario:**
```javascript
1. Navigate to Make.com dashboard
   URL: <<MAKE_SCENARIO_URL>>

2. Review recent executions:
   - Slack webhook triggered
   - Airtable connection successful
   - No errors in log

3. Verify Airtable → Notion sync:
   - Airtable has matching entry
   - Notion Inbox Log has matching entry
   - Data fields match
```
## "Done" Definition
**Phase 1 capture is working when:**
- Slack DM to bot → entry in Inbox Log (< 5 seconds)
- Slack slash command → entry in Inbox Log (< 5 seconds)
- Manual Notion entry → saved to Inbox Log immediately
- Every entry has:
    - ✅ Raw Input (not empty)
    - ✅ Timestamp (current time)
    - ✅ Source (correct channel)
    - ✅ Status (defaults to "New")
- Webhook errors are caught and logged (not silent failures)
- Inbox Log is the single source of truth for all captures
**Not required in Phase 1:**
- Classification (Phase 2)
- Auto-routing to destination databases (Phase 2)
- Confidence scoring (Phase 2)
- Structured extraction (Phase 2+)
## Exit Criteria
**Phase 1 is complete when:**
- [ ] Slack bot DM capture tested and working
- [ ] Slack slash command tested and working
- [ ] Manual Notion entry tested and working
- [ ] Inbox Log database has required fields:
    - Raw Input (text)
    - Timestamp (date with time)
    - Source (select)
    - Status (select)
    - Routing Prefix (text)
- [ ] [Make.com](http://make.com/) scenario tested:
    - Slack webhook → Airtable → Notion
    - End-to-end latency < 10 seconds
    - Error handling active
- [ ] 10+ test entries in Inbox Log with variety:
    - Different sources (Slack DM, slash command, manual)
    - Different routing prefixes (PRO, BD, CAL, R, fix)
    - Mix of short and long inputs
- [ ] No silent failures (all errors visible in [Make.com](http://make.com/) logs)
- [ ] Inbox Log integrity verified:
    - No duplicate entries
    - All timestamps accurate
    - No missing Raw Input fields
- [ ] Documentation updated:
    - Routing prefix conventions documented
    - Capture workflow documented
    - Troubleshooting guide added
**Once exit criteria met, Phase 1 is complete.**
## Next Phase
Proceed to Phase 2: Classification & Routing.
**Phase 2 will add:**
- LLM-based classification (Claude/Perplexity)
- Confidence scoring
- Auto-routing to destination databases
- Structured field extraction
## Troubleshooting
### Problem: Slack bot not responding
**Check:**
```javascript
1. Verify bot is online in Slack workspace
2. Check Make.com scenario status (active/paused)
3. Review Make.com execution log for errors
4. Verify webhook URL is correct:
   - Slack app settings → Event Subscriptions
   - Request URL should match Make webhook
5. Check Slack app permissions:
   - Bot needs `chat:write` scope
   - App must be installed in workspace
```
### Problem: Entries not appearing in Notion
**Check:**
```javascript
1. Verify Airtable has entry (if using Airtable sync)
2. Check Notion API token is valid:
   - Test connection in Make.com
   - Refresh token if expired
3. Verify Inbox Log database URL is correct in Make scenario
4. Check Notion integration permissions:
   - Integration has access to Inbox Log
   - Page sharing settings allow integration
```
### Problem: Duplicate entries
**Resolution:**
```javascript
1. Review Make.com scenario for retry logic
2. Add deduplication check:
   - Check if timestamp + Raw Input already exists
   - Skip if duplicate detected
3. Set webhook timeout appropriately (5-10 seconds)
```
### Problem: Webhook rate limiting
**Symptoms:**
```javascript
- HTTP 429 errors in Make.com log
- Delayed or dropped messages
```
**Resolution:**
```javascript
1. Add rate limiting in Make scenario:
   - Max 10 requests/second to Notion API
   - Queue messages if limit exceeded
2. Consider batching if high volume:
   - Collect messages for 1 minute
   - Bulk insert to Notion
```
## Mirror Note
**This page exports to:**
```javascript
phases/phase_1_capture.md
```
**Publish safety rules:**
- No real secrets (use `<<PLACEHOLDERS>>`)
- No real webhook URLs (use `<<MAKE_WEBHOOK_URL>>`)
- No real Notion tokens (use `<<NOTION_API_TOKEN>>`)
- Example credentials must have `EXAMPLE_SECRET:` prefix on same line
- Drift logging is Notion-only (no mention of public drift log files)
**When exporting:**
1. Verify all placeholders are in correct format
1. Strip any linkified filenames from Notion export
1. Run secret scan before committing:
```bash
bash checks/scan_secrets.sh
```
1. Follow mirror procedure in protocols/MIRRORING.md
**Child page:** phases/phase_2_classification.md
# Phase 2: Classification & Routing
## Objective
Turn captured brain dumps into classified, routed entries with confidence scores. Establish manual classification workflow first, then layer in LLM automation.
## Inputs (from Phase 1)
**Source:** Inbox Log database
**Entry structure:**
```yaml
- Raw Input: text (brain dump content)
- Timestamp: date (capture time)
- Source: select (Slack, Manual, Email)
- Status: select (New, Processed, Archived)
- Routing Prefix: text (extracted prefix like PRO:, BD:, etc.)
```
**Phase 2 adds:**
```yaml
- Classification Confidence: number (0.00 to 1.00)
- Destination: relation (links to target database)
- Processing Notes: text (classification reasoning)
```
## Classification Scheme
**Routing prefixes defined in governance:**
See repo governance for authoritative routing rules.
**Prefix definitions:**
- **PRO:** Project extraction (confidence 1.0, deterministic destination Projects, extraction-only)
    - Runs LLM extraction to populate structured fields
    - No classification step needed (destination fixed)
    - Always auto-files to Projects database
- **BD:** Brain dump (requires LLM classification)
    - Needs semantic analysis
    - Destination determined by content
    - May route to Projects, People, Ideas, Admin, or Events
- **CAL:** Calendar/event (scaffolded in Phase 2)
    - Event scheduling requests
    - Date/time extraction needed
    - Destination: Events database
- **R:** Research (scaffolded in Phase 2)
    - Research tasks or queries
    - Destination: Research Jobs database
- **fix:** Corrections (scaffolded in Phase 2)
    - Updates to existing entries
    - Requires lookup and update logic
    - Destination: varies based on target
**Classification process:**
1. **Extract prefix** from Raw Input (first line or leading text)
1. **Score confidence** (0.00 to 1.00)
1. **Determine destination** database
1. **Route entry** (auto if confidence ≥ threshold, manual review if below)
## Confidence Thresholds
**Threshold defined in governance:**
The governance document specifies the auto-file threshold.
**Scoring rules:**
```yaml
Confidence = 1.0:
  - PRO: prefix (always bypass LLM, direct extraction)
  - Explicit, unambiguous routing
  - No semantic analysis needed

Confidence ≥ 0.60:
  - Auto-file to destination
  - LLM classification passed threshold
  - Operator review optional

Confidence < 0.60:
  - Manual review required
  - Entry stays in Inbox Log
  - Status = "Needs Review"
  - Operator assigns destination
```
**Example classifications:**
```yaml
Input: "PRO: Update mirror docs Phase 2 by Friday"
  Prefix: PRO
  Confidence: 1.0
  Destination: Projects
  Action: Auto-file

Input: "BD: Interesting conversation about AI governance frameworks"
  Prefix: BD
  Confidence: 0.75 (LLM scored)
  Destination: Ideas (LLM determined)
  Action: Auto-file

Input: "BD: Something about that thing we discussed"
  Prefix: BD
  Confidence: 0.35 (LLM scored low)
  Destination: Unknown
  Action: Needs Review
```
## Output Destinations (Notion DB Targets)
**Destination databases:**
```yaml
Projects:
  - Structured project tracking
  - Fields: Project Name, Status, Due Date, Owner, Notes
  - High confidence routing

People:
  - Contact and relationship tracking
  - Fields: Name, Role, Company, Notes, Last Contact
  - Requires person entity extraction

Ideas:
  - Unstructured idea capture
  - Fields: Title, Description, Category, Status
  - Low friction, high volume

Admin:
  - Administrative tasks and notes
  - Fields: Task, Priority, Due Date, Status
  - Catch-all for operational items

Events:
  - Calendar and scheduling
  - Fields: Title, Date/Time, Attendees, Location, Notes
  - Requires date/time extraction (Phase 2 scaffolded)

Research Jobs:
  - Research tasks and queries
  - Fields: Query, Status, Priority, Results
  - Links to Articles, Drafts, Publications
  - (Phase 3+, scaffolded in Phase 2)
```
## Manual Workflow (Phase 2 Initial)
**Current state: Operator-driven classification**
### Step 1: Review Inbox Log
```bash
# Open Notion
# Navigate to: Brain Stem Project → Inbox Log
# Filter: Status = "New"
```
### Step 2: Classify Entry
**For each entry:**
1. **Read Raw Input**
1. **Identify routing prefix** (if present)
1. **Determine destination:**
    - PRO: → Projects (confidence 1.0)
    - BD: → Operator decides based on content
    - CAL: → Events (scaffolded)
    - R: → Research Jobs (scaffolded)
    - fix: → Target database (scaffolded)
1. **Assign confidence:**
    - Clear and unambiguous: 0.80-1.0
    - Requires interpretation: 0.40-0.79
    - Unclear or incomplete: 0.0-0.39
1. **Update Inbox Log entry:**
    - Set Classification Confidence field
    - Set Destination relation
    - Add Processing Notes (optional)
    - Change Status to "Processed"
### Step 3: Create Destination Entry
**If confidence ≥ threshold (0.60):**
```bash
# Create new entry in destination database
# Copy relevant data from Raw Input
# Link back to Inbox Log entry (audit trail)
# Mark Inbox Log Status = "Processed"
```
**If confidence < threshold:**
```bash
# Leave in Inbox Log
# Set Status = "Needs Review"
# Add Processing Notes explaining uncertainty
# Revisit later or request clarification
```
## Automation (Phase 2 Planned, Not Implemented Yet)
**Future LLM classification workflow:**
```yaml
Trigger:
  - New entry in Inbox Log
  - Status = "New"
  - Routing Prefix extracted

Process:
  1. PRO: prefix → confidence = 1.0, run extraction-only (no classification), auto-file to Projects
  2. Other prefixes → send to LLM (Claude/Perplexity)
  3. LLM returns:
     - Classification label
     - Confidence score (0.00-1.00)
     - Destination database
     - Reasoning (for Processing Notes)
  4. If confidence ≥ 0.60:
     - Auto-create entry in destination
     - Update Inbox Log (Processed)
     - Log success
  5. If confidence < 0.60:
     - Update Inbox Log (Needs Review)
     - Notify operator
     - Wait for manual classification

LLM Prompt Structure:
  - System: Classification rules from governance
  - User: Raw Input text
  - Output: JSON with label, confidence, destination, reasoning

API Integration:
  - Make.com scenario
  - Claude API: <<CLAUDE_API_KEY>>
  - Notion API: <<NOTION_API_TOKEN>>
  - Airtable (intermediate if needed): <<AIRTABLE_PAT>>
```
**Phase 2 scope:**
- Manual classification workflow validated
- Destination databases created and tested
- Confidence scoring documented
- LLM integration designed (not implemented)
- Operator can process 10+ entries efficiently
**Phase 3+ scope (future):**
- LLM auto-classification implemented
- Structured field extraction (dates, people, projects)
- Batch processing
- Feedback loop (operator corrections improve LLM)
## Governance References
**Repo governance documents:**
```javascript
CONTRACT.md
contracts/spec.yaml
contracts/routes.yaml
contracts/AI_COLLABORATION.md
checks/scan_secrets.sh
```
**Key governance rules:**
- Routing prefixes and confidence thresholds defined in routes.yaml
- Auto-file threshold (auto_file_confidence_min) defined in routes.yaml
- Invariants for classification integrity defined in spec.yaml
- Secret scan enforces publish safety (no real credentials)
## Exit Criteria
**Phase 2 is complete when:**
- [ ] All destination databases created:
    - Projects
    - People
    - Ideas
    - Admin
    - Events (scaffolded)
    - Research Jobs (scaffolded)
- [ ] Inbox Log extended with Phase 2 fields:
    - Classification Confidence (number)
    - Destination (relation)
    - Processing Notes (text)
- [ ] Manual classification workflow documented and tested
- [ ] Operator can classify 10+ entries:
    - Extract routing prefix
    - Assign confidence score
    - Select destination database
    - Create entry in destination
    - Update Inbox Log status
- [ ] Confidence threshold (0.60) validated:
    - High confidence entries (≥ 0.60) route cleanly
    - Low confidence entries (< 0.60) flagged for review
    - No ambiguous auto-files
- [ ] PRO: prefix extraction tested:
    - PRO entries always confidence 1.0
    - LLM extraction populates Projects fields
    - Auto-file to Projects (no classification)
    - < 2 seconds processing time
- [ ] Audit trail maintained:
    - Inbox Log preserves all raw inputs
    - Destination entries link back to Inbox Log
    - No data loss in routing
- [ ] Documentation updated:
    - Classification scheme documented
    - Confidence scoring guidelines documented
    - Manual workflow procedure documented
- [ ] LLM integration designed (not implemented):
    - API endpoints identified
    - Prompt templates drafted
    - Error handling designed
    - Ready for Phase 3 implementation
**Once exit criteria met, Phase 2 is complete.**
## Next Phase
Proceed to Phase 3: Research Pipeline (LLM classification automation).
**Phase 3 will add:**
- Claude/Perplexity API integration
- Auto-classification for BD: prefix entries
- Confidence scoring automation
- Batch processing
- Operator feedback loop
## Troubleshooting
### Problem: Unclear routing prefix
**Symptoms:**
- Entry has no prefix or ambiguous prefix
- Operator unsure which database to target
**Resolution:**
```javascript
1. Check Raw Input for implicit signals:
   - Person names → People
   - Project names → Projects
   - Dates/times → Events
   - Questions → Research Jobs or Ideas
2. If still unclear:
   - Set confidence = 0.30 (low)
   - Status = "Needs Review"
   - Add Processing Notes: "Ambiguous content, requires clarification"
   - Follow up with original author if possible
```
### Problem: Confidence score inconsistent
**Symptoms:**
- Different operators assign different scores to similar entries
- No clear scoring guidelines
**Resolution:**
```javascript
1. Document scoring rubric:
   - 1.0 = Explicit prefix (PRO:) or unambiguous content
   - 0.8-0.9 = Clear intent, minor interpretation needed
   - 0.6-0.79 = Requires moderate interpretation, reasonable confidence
   - 0.4-0.59 = Ambiguous, multiple destinations possible
   - 0.0-0.39 = Unclear, needs clarification
2. Calibrate with test set:
   - Classify 20 test entries
   - Compare operator scores
   - Discuss discrepancies
   - Refine rubric
3. Review periodically as volume increases
```
### Problem: Destination database missing fields
**Symptoms:**
- Cannot fully populate destination entry
- Fields in Inbox Log Raw Input don't map to destination schema
**Resolution:**
```javascript
1. Review destination database schema
2. Add missing fields if needed (update governance first)
3. Or: adjust extraction expectations
   - Store partial data
   - Flag for enrichment later
   - Don't block on missing optional fields
4. Document field mapping:
   - Inbox Log Raw Input → Destination fields
   - Clear examples for each destination
```
### Problem: Auto-file threshold too low/high
**Symptoms:**
- Too many low-quality auto-files (threshold too low)
- Too many manual reviews (threshold too high)
**Resolution:**
```javascript
1. Review classified entries over 1 week:
   - Count auto-files that needed correction
   - Count manual reviews that were obvious
2. Adjust threshold in governance (contracts/routes.yaml):
   - If ≥ 10% auto-files wrong → raise threshold
   - If ≥ 50% manual reviews obvious → lower threshold
3. Document change in changelog/
4. Re-test with new threshold
```
## Mirror Note
This page exports to `phases/phase_2_classification.mc`and must remain publish-safe.
**Child page:** protocols/OPERATING.md
# Operating Protocol (Mirror System)
## Purpose
Daily runbook for maintaining the Notion ↔ GitHub public mirror system for `sharedterrain/brainstem-docs`.
## Daily/Weekly Operations
**Daily:**
- Check GitHub Actions status for failed CI runs
- Review any open PRs waiting for merge
- Monitor operational Drift Log for unresolved items
**Weekly:**
- Run drift detection reconciliation checklist
- Review "Currently Published" tracker vs actual repo state
- Check for orphaned files (in repo but no Notion source)
- Verify mirror status banners on Notion pages match reality
**Monthly:**
- Full drift audit (compare all Notion pages marked `[Mirrored to GitHub]` to repo files)
- Review and update placeholder patterns if needed
- Archive old changelog entries
## Pre-Publish Checklist
**Before exporting from Notion:**
- [ ] Content marked `[Mirrored to GitHub]` in Notion
- [ ] GitHub path documented on page
- [ ] All sensitive values replaced with placeholders:
```javascript
<<SLACK_WEBHOOK_URL>>
<<AIRTABLE_API_KEY>>
<<NOTION_TOKEN>>
```
- [ ] Secret-like examples prefixed with `EXAMPLE_SECRET:` on same line
- [ ] File paths inside code blocks (prevents linkification)
**Before committing to dev:**
- [ ] Exported markdown sanitized (strip any auto-linkified filenames)
- [ ] Files placed in correct repo paths per publish scope
- [ ] Local secret scan passes:
```bash
bash checks/scan_secrets.sh
```
**Before merging PR:**
- [ ] CI check `scan-secrets` passes on GitHub
- [ ] PR description references Notion source pages
- [ ] Branch is up-to-date with main
## Troubleshooting
### Secret Scan Failures
**Symptom:** `scan-secrets` fails in CI or locally
**Diagnosis:**
```bash
bash checks/scan_secrets.sh
# Output shows matched pattern and line number
```
**Resolution:**
1. **Real secret detected:**
    - Replace with placeholder: `<<DESCRIPTIVE_NAME>>`
    - Re-run scan
    - Never commit real credentials
1. **Intentional example:**
    - Add `EXAMPLE_SECRET:` marker on same line
    - Example:
```bash
EXAMPLE_SECRET: curl -H "Authorization: Bearer demo_abc123" https://api.example.com
```
    - Re-run scan
1. **False positive:**
    - Review pattern in:
```javascript
automation/redaction_patterns.txt
```
    - If pattern too broad, refine it (requires PR + CI pass)
    - Document in change control
### Linkification in Exports
**Symptom:** Notion export contains linked filenames like `[`[`README.md`](http://readme.md/)`](`[`http://readme.md/`](http://readme.md/)`)`
**Prevention:**
- Put file paths in code blocks when writing Notion content
- Example:
```javascript
See `contracts/spec.yaml` for details.
```
**Cleanup:**
- Manual find/replace before committing:
    - Find: `[`[`filename.md`](http://filename.md/)`](`[`http://filename.md/`](http://filename.md/)`)`
    - Replace: `filename.md`
- Or use inline code: Find `[\`file`](url)`, replace with ``file``
### Drift Detected
**Symptom:** Notion content differs from repo file
**Resolution priority:**
1. **Content/planning drift:** Notion wins → update repo
1. **CI behavior drift:** Repo wins → update Notion to document actual behavior
1. **Timestamp conflict:** Use most recent, document reconciliation
**Steps:**
- Compare Notion page to repo file
- Determine source of truth per resolution priority
- Update lagging system
- Record in operational Drift Log
## Repo Workflow (dev → main PR)
**Standard flow:**
```bash
# 1. Switch to dev and pull latest
cd ~/code/brainstem-docs
git checkout dev
git pull origin dev

# 2. Copy exported files to repo
cp [source] [target]

# 3. Validate locally
bash checks/scan_secrets.sh

# 4. Stage and commit
git add .
git commit -m "docs: [description]

Notion sources:
- [page URLs or titles]"

# 5. Push to dev
git push origin dev

# 6. Create PR on GitHub (dev → main)
# Wait for CI to pass

# 7. Merge PR

# 8. Backfill Notion (see below)
```
**Branch protection rules:**
- PRs required before merge to main
- Status check `scan-secrets` must pass
- Branch must be up-to-date with main
## Notion Backfill Rule (Git-First Changes)
**Normal rule:** Notion is canonical → changes flow Notion → Git
**Exception:** Git-first hotfix (urgent CI fix, repo-breaking issue)
**If you made changes directly in Git:**
1. **Merge the fix** (dev → main)
1. **Within 24 hours, backfill Notion:**
    - Update corresponding Notion page to match repo
    - Add note: `[Backfilled from GitHub hotfix YYYY-MM-DD]`
    - Add entry to operational Drift Log with explanation
1. **Document why** hotfix was necessary
1. **Update pre-publish checklist** if hotfix revealed a gap
**When NOT to use Git-first:**
- Routine content updates (always use Notion → Git flow)
- New features or protocol changes (plan in Notion first)
- Non-urgent corrections (use normal flow)
## Post-Merge Checklist
**After PR merged to main:**
- [ ] Pull latest from main:
```bash
git checkout main
git pull origin main
```
- [ ] Update Notion pages:
    - Add `Last Mirror Date: YYYY-MM-DD`
    - Update operational Drift Log
    - Update "Currently Published" tracker
- [ ] Verify published at:
```javascript
https://github.com/sharedterrain/brainstem-docs
```
## Emergency Contacts
- **Repo owner:** `<<GITHUB_USERNAME>>`
- **Notion workspace:** `<<NOTION_WORKSPACE_ID>>`
- **Maintainer:** `<<MAINTAINER_NAME>>`
## Quick Reference
**Publish scope paths:**
```javascript
CONTRACT.md
README.md
contracts/
protocols/
phases/
checks/
automation/
changelog/
reports/
```
**Placeholder format:**
```javascript
<<ALL_CAPS_WITH_UNDERSCORES>>
```
**Example secret marker:**
```javascript
EXAMPLE_SECRET:
```
**Secret scan command:**
```bash
bash checks/scan_secrets.sh
```
**Child page:** Repo Mirror Ground Truth Snapshot (brainstem-docs)
**Purpose:** Authoritative snapshot of the actual `sharedterrain/brainstem-docs` repo state for reconciliation and mapping.
---
## Metadata
- **Repo:** `sharedterrain/brainstem-docs`
- **Snapshot branch:** `dev`
- **Snapshot date/time:** 2026-02-05 ~20:54 PST (from git log HEAD timestamp)
## Repo root listing
```bash
# ls -la
total 16
drwxr-xr-x  15 jedidiahduyf  staff  480 Feb  5 19:37 .
drwxr-xr-x   3 jedidiahduyf  staff   96 Feb  4 12:59 ..
drwxr-xr-x   3 jedidiahduyf  staff   96 Feb  4 15:31 .claude
drwxr-xr-x  15 jedidiahduyf  staff  480 Feb  5 20:54 .git
drwxr-xr-x   3 jedidiahduyf  staff   96 Feb  5 19:37 .github
-rw-r--r--   1 jedidiahduyf  staff  892 Feb  4 15:29 CONTRACT.md
-rw-r--r--   1 jedidiahduyf  staff  891 Feb  4 15:29 README.md
drwxr-xr-x   4 jedidiahduyf  staff  128 Feb  5 20:36 automation
drwxr-xr-x   3 jedidiahduyf  staff   96 Feb  4 15:29 changelog
drwxr-xr-x   4 jedidiahduyf  staff  128 Feb  5 19:37 checks
drwxr-xr-x   6 jedidiahduyf  staff  192 Feb  5 20:54 contracts
drwxr-xr-x   3 jedidiahduyf  staff   96 Feb  4 15:29 examples
drwxr-xr-x   4 jedidiahduyf  staff  128 Feb  5 19:37 phases
drwxr-xr-x   5 jedidiahduyf  staff  160 Feb  5 19:37 protocols
drwxr-xr-x   3 jedidiahduyf  staff   96 Feb  4 15:29 reports
```
## Key folder listings
```bash
# ls -la contracts protocols checks automation changelog

automation:
total 16
drwxr-xr-x   4 jedidiahduyf  staff  128 Feb  5 20:36 .
drwxr-xr-x  15 jedidiahduyf  staff  480 Feb  5 19:37 ..
-rw-r--r--   1 jedidiahduyf  staff    4 Feb  4 15:29 .gitkeep
-rw-r--r--   1 jedidiahduyf  staff  364 Feb  5 20:36 redaction_patterns.txt

changelog:
total 8
drwxr-xr-x   3 jedidiahduyf  staff   96 Feb  4 15:29 .
drwxr-xr-x  15 jedidiahduyf  staff  480 Feb  5 19:37 ..
-rw-r--r--   1 jedidiahduyf  staff    4 Feb  4 15:29 .gitkeep

checks:
total 16
drwxr-xr-x   4 jedidiahduyf  staff   128 Feb  5 19:37 .
drwxr-xr-x  15 jedidiahduyf  staff   480 Feb  5 19:37 ..
-rw-r--r--   1 jedidiahduyf  staff     4 Feb  4 15:29 .gitkeep
-rwxr-xr-x   1 jedidiahduyf  staff  1658 Feb  5 19:37 scan_secrets.sh

contracts:
total 32
drwxr-xr-x   6 jedidiahduyf  staff   192 Feb  5 20:54 .
drwxr-xr-x  15 jedidiahduyf  staff   480 Feb  5 19:37 ..
-rw-r--r--   1 jedidiahduyf  staff     4 Feb  4 15:29 .gitkeep
-rw-r--r--   1 jedidiahduyf  staff  1585 Feb  5 20:54 AI_COLLABORATION.md
-rw-r--r--   1 jedidiahduyf  staff  1164 Feb  5 20:35 routes.yaml
-rw-r--r--   1 jedidiahduyf  staff  2201 Feb  5 20:54 spec.yaml

protocols:
total 24
drwxr-xr-x   5 jedidiahduyf  staff   160 Feb  5 19:37 .
drwxr-xr-x  15 jedidiahduyf  staff   480 Feb  5 19:37 ..
-rw-r--r--   1 jedidiahduyf  staff     4 Feb  4 15:29 .gitkeep
-rw-r--r--   1 jedidiahduyf  staff   944 Feb  4 15:29 PUBLISHING.md
-rw-r--r--   1 jedidiahduyf  staff  1719 Feb  5 19:37 SECURITY.md
```
## Contracts
### contracts/spec.yaml
```yaml
version: "0.1.0"
project: "brainstem-docs"

mirror:
  publish_scope:
    # Only these paths are allowed to appear in the public mirror.
    paths:
      - "CONTRACT.md"
      - "README.md"
      - "contracts/"
      - "protocols/"
      - "phases/"
      - "checks/"
      - "automation/"
      - "changelog/"
      - "reports/"
    disallowed:
      # Anything outside publish_scope is considered private / out-of-scope.
      outside_publish_scope: true

security:
  placeholders:
    # Placeholders MUST use this format in public docs.
    format: "<<ALL_CAPS_WITH_UNDERSCORES>>"
    examples:
      - "<<MAKE_WEBHOOK_URL>>"
      - "<<SLACK_BOT_TOKEN>>"
      - "<<CLAUDE_API_KEY>>"
      - "<<AIRTABLE_PAT>>"
      - "<<NOTION_TOKEN>>"
      - "<<REDACTED>>"
  example_marker:
    # If a doc needs to include secret-like example strings, they MUST be marked on the same line.
    # The CI secret scan ignores lines containing this marker.
    marker: "EXAMPLE_SECRET:"
    rule: "Any placeholder secret/token/webhook example must be prefixed with EXAMPLE_SECRET: on the same line."

checks:
  # CI checks that must pass for PRs into main.
  required:
    - id: "scan_secrets"
      script: "checks/scan_secrets.sh"
      severity: "high"
      scope: "mirror.publish_scope"
      notes:
        - "Ignores lines containing EXAMPLE_SECRET:"
        - "Excludes protocols/SECURITY.md and automation/redaction_patterns.txt from grep recursion"
  recommended:
    - id: "markdown_lint"
      severity: "medium"
      notes:
        - "Optional: add later if needed"

invariants:
  - id: "no_secrets_in_public_mirror"
    severity: "high"
    description: "Public mirror must not contain real credentials, tokens, webhook URLs, or private keys."
  - id: "placeholders_only"
    severity: "high"
    description: "Sensitive values must be represented as placeholders (<<ALL_CAPS_WITH_UNDERSCORES>>)."
  - id: "examples_must_be_marked"
    severity: "high"
    description: "Any secret-like example string must be prefixed with EXAMPLE_SECRET: on the same line."
  - id: "publish_scope_only"
    severity: "high"
    description: "Only approved publish_scope paths may be included in the public mirror repo."
```
### contracts/routes.yaml
```yaml
version: "0.1.0"
project: "brainstem"

thresholds:
  auto_file_confidence_min: 0.60

routes:
  - prefix: "PRO:"
    destination: "projects"
    llm_mode: "bypass"
    rule: "always_file"
    implementation_state: "planned"

  - prefix: "BD:"
    destination: "llm_classified"
    llm_mode: "classify"
    rule: "confidence_based"
    implementation_state: "planned"

  - prefix: "CAL:"
    destination: "events"
    llm_mode: "extract"
    rule: "planned"
    implementation_state: "planned"

  - prefix: "R:"
    destination: "research_jobs"
    llm_mode: "planned"
    rule: "planned"
    implementation_state: "planned"

  - prefix: "fix:"
    destination: "corrections"
    llm_mode: "planned"
    rule: "planned"
    implementation_state: "planned"

data_contracts:
  tables_required:
    - "People"
    - "Projects"
    - "Ideas"
    - "Admin"
    - "Events"
    - "Inbox Log"

invariants:
  - id: "no_secrets_in_repo"
    severity: "high"
    description: "Repo must not contain credentials, tokens, webhook URLs, or private keys."
  - id: "placeholders_only"
    severity: "high"
    description: "Sensitive values must be represented as <<PLACEHOLDER>>."
```
### contracts/AI_[COLLABORATION.md](http://collaboration.md/)
```markdown
# AI Collaboration Contract (Brainstem Docs)

This repo is a public mirror. Any agent (ChatGPT, Claude, Notion AI, scripts) MUST follow these rules when producing or editing content that may be published here.

## Scope

- This contract applies to all content in publish scope:
  - CONTRACT.md, README.md
  - contracts/, protocols/, phases/, checks/, automation/, changelog/, reports/

## Non-negotiable invariants

1) **No secrets in public mirror**
   - Never include real credentials, API keys, tokens, private keys, session cookies, or real webhook URLs.

2) **Placeholders only**
   - Any sensitive value must be represented as a placeholder:
     - Format: `<<ALL_CAPS_WITH_UNDERSCORES>>`
     - Examples: `<<NOTION_TOKEN>>`, `<<MAKE_WEBHOOK_URL>>`, `<<SLACK_BOT_TOKEN>>`

3) **Examples must be marked**
   - If documentation needs to show secret-like example strings (e.g., token prefixes, key headers, webhook domains), the line MUST be prefixed with:
     - `EXAMPLE_SECRET:`
   - CI secret scanning ignores lines containing `EXAMPLE_SECRET:`. Unmarked secret-like strings will fail CI.

## How agents should propose changes

- Prefer small, reviewable diffs.
- Do not rename/move files without updating references in docs and contracts.
- If CI fails, first fix the smallest change that makes CI green (do not widen exclusions unless necessary).

## Definition of "publish safe"

A change is publish safe if:
- It stays inside publish scope
- It introduces no real secrets
- Any secret-like example strings are explicitly marked with `EXAMPLE_SECRET:`
- `checks/scan_secrets.sh` passes on PR
```
## CI / automation
### checks/scan_[secrets.sh](http://secrets.sh/)
```bash
#!/bin/bash
set -eu
set -o pipefail

echo "🔍 Scanning for secrets in public mirror scope..."

PATTERN_FILE="automation/redaction_patterns.txt"

PUBLISH_PATHS=(
  "contracts/"
  "protocols/"
  "phases/"
  "checks/"
  "automation/"
  "README.md"
  "changelog"
  "CONTRACT.md"
)

if [ ! -f "$PATTERN_FILE" ]; then
  echo "❌ Missing $PATTERN_FILE"
  exit 1
fi

# Build an alternation regex from non-empty lines (strip CR, join with |)
patterns="$(
  grep -vE '^[[:space:]]*$' "$PATTERN_FILE" \
    | tr -d '\r' \
    | paste -sd'|' -
)"

if [ -z "$patterns" ]; then
  echo "❌ No patterns found in $PATTERN_FILE"
  exit 1
fi

# Ignore matches explicitly marked as example placeholders
IGNORE_MARKER="EXAMPLE_SECRET:"

scan_path() {
  local path="$1"

  if [ -d "$path" ]; then
    # Print matches, then filter out approved example lines
    local matches
    matches="$(grep -RInE --exclude="SECURITY.md" --exclude="redaction_patterns.txt" "$patterns" "$path" 2>/dev/null || true)"
    matches="$(printf '%s\n' "$matches" | grep -vF "$IGNORE_MARKER" || true)"

    if [ -n "$matches" ]; then
      printf '%s\n' "$matches"
      echo "❌ SECRETS DETECTED in $path - DO NOT COMMIT"
      exit 1
    fi
  else
    local matches
    matches="$(grep -InE "$patterns" "$path" 2>/dev/null || true)"
    matches="$(printf '%s\n' "$matches" | grep -vF "$IGNORE_MARKER" || true)"

    if [ -n "$matches" ]; then
      printf '%s\n' "$matches"
      echo "❌ SECRETS DETECTED in $path - DO NOT COMMIT"
      exit 1
    fi
  fi
}

for path in "${PUBLISH_PATHS[@]}"; do
  [ -e "$path" ] || continue
  scan_path "$path"
done

echo "✅ No secrets found in publish scope"
```
### automation/redaction_patterns.txt
```javascript
# Redaction patterns (public mirror)
# Use these as search patterns before committing.
hook.make.com
https://hook.
xoxb-
xoxp-
sk-ant-
Authorization: Bearer
BEGIN PRIVATE KEY
api.airtable.com/v0/app
secret_
# If found, replace the entire value with a placeholder:
# <<MAKE_WEBHOOK_URL>>
# <<SLACK_BOT_TOKEN>>
# <<CLAUDE_API_KEY>>
# <<AIRTABLE_PAT>>
# <<REDACTED>>
```
## File inventories
### Protocols
```javascript
protocols/PUBLISHING.md
protocols/.gitkeep
protocols/SECURITY.md
```
### Changelog
```javascript
changelog/.gitkeep
```
**(Empty: no changelog entries yet)**
## Recent commits
```javascript
2911e19 (HEAD -> dev, origin/dev) fix: avoid secret-scan false positive in governance spec
b98bffc merge: sync dev with main
c3bf12f chore: add mirror governance spec and AI collaboration contract
80f2f83 (origin/main, origin/HEAD, main) Fix secret-scan: ignore EXAMPLE_SECRET placeholders, tighten patterns
0e4eb4e fix: make secret scan durable with EXAMPLE_SECRET markers
3a2e004 fix: prevent empty pattern matching in secret scan
341c16c chore: add secret scan script
99c567e ci: add validate workflow
56ed3d3 docs: update Phase 0 instructions
34e58a6 docs: add phase 0 skeleton
ba9e7c3 docs: scaffold repo
6c046ce chore: add protocols folder
8fef96e chore: add protocols folder
176ad9d Initial commit
```

Brain Stem mirror mapping and project-specific mirror config. The export scope mapping in Phase 1 covers this need for now.

**Child database:** Friction Log

**Child database:** Export Scope Mapping — fires Make webhook → repository_dispatch → GitHub Action → converts and commits all active pages

**Child page:** Make Scenario Build Reference
Complete build reference for the **Mirror Bulk Publish** system.
> ⚠️ **v2 Architecture — March 2026.** This page was rewritten to reflect the current as-built system. The previous version (v1) documented an 11-module Make scenario that handled fetching, encoding, and per-page commits. That architecture was retired after operational testing. See *What Changed and Why* below.
---
## Architecture Overview
**Make Scenario (trigger only):**
Make receives a webhook and POSTs a `repository_dispatch` event to GitHub. That's it — no fetching, no encoding, no iteration, no per-page commits.
**GitHub Action (all conversion work):**
Triggered by `repository_dispatch` (from Make) or `workflow_dispatch` (manual from GitHub UI). Runs a Python script that:
1. Reads active page mappings from Export Scope Mapping (via Notion API)
1. Fetches all blocks for each page with full pagination (no 100-block limit)
1. Converts Notion blocks to clean markdown
1. Commits all `.md` files in a single atomic commit
**Key principles:**
- Make wires, it does not transform
- All transformation logic lives in version-controlled Python
- Single atomic commit eliminates race conditions
- Notion API pagination handled in code (no truncation)
- n8n migration only requires rewiring the dispatch trigger
- `NOTION_API_TOKEN` stored as a GitHub Secret (used by Action, not Make)
---
## What Changed and Why
| **Problem (v1)** | **Root Cause** | **Fix (v2)** |  |
| --- | --- | --- | --- |
| 7 simultaneous commits caused race conditions | Make committed per-page inside iterator loop | Single atomic `git add . && git commit` in Action |  |
| GitHub Actions cancelled each other | Each Make commit triggered a separate Action run | One dispatch → one Action run |  |
| Make self-deactivated on conflicts | Git push conflicts from concurrent commits | No Git operations in Make at all |  |
| Large documents truncated | Notion API 100-block limit, no pagination in Make | Python script paginates with `has_more` / `next_cursor` |  |
| Source Page URL resolved to wrong page ID | Notion AI compressed URL blind spot when populating db | Python script reads page IDs from Export Scope Mapping via API |  |
**Root architectural lesson:** Make is a wiring tool. Loops, pagination, encoding, and file manipulation are code problems. Solving them in Make required 11 modules and elaborate error handling for something a 100-line Python script does trivially. See Working Agreements §4 candidate (FR-20260302-001).
---
## Decisions
**1. Path column stays **`.md`
The markdown path is the canonical output. The Python script derives all intermediate paths internally.
**2. Make does not touch Notion content**
Make never calls the Notion blocks API. It only triggers the GitHub Action. This eliminates the entire class of problems from v1 (truncation, encoding, per-page commits).
**3. NOTION_API_TOKEN in GitHub Secrets**
The Notion token is now primarily consumed by the GitHub Action, not Make. Make only needs the GitHub token (to POST `repository_dispatch`).
---
## Make Scenario — Module List (v2)
| **#** | **Module Type** | **Name** | **Purpose** |
| --- | --- | --- | --- |
| 1 | Webhooks → Custom webhook | Trigger | Receives publish request |
| 2 | HTTP → Make a request | Dispatch to GitHub | POSTs repository_dispatch event to trigger the Action |
That's it. Two modules.
---
## Module 1: Trigger (Webhooks → Custom webhook)
Same as v1. Receives the publish request (from Slack trigger scenario, manual call, or Notion button).
---
## Module 2: Dispatch to GitHub (HTTP → Make a request)
**Method:** POST
**URL:**
```plain text
https://api.github.com/repos/sharedterrain/notion-mirror/dispatches
```
**Headers:**
- Authorization: Bearer <<GITHUB_TOKEN>>
- Accept: application/vnd.github+json
- Content-Type: application/json
**Body type:** Raw
**Content type:** JSON (application/json)
**Request content:**
```json
{"event_type": "notion-mirror"}
```
**Parse response:** No
**Note:** GitHub returns 204 No Content on success. The Action runs asynchronously — Make does not wait for it to complete.
---
## GitHub Action — Convert and Commit
**File:** `.github/workflows/convert.yml`
**Triggers:**
- `workflow_dispatch` — manual trigger from GitHub UI
- `repository_dispatch` types: [notion-mirror] — triggered by Make
**Steps:**
1. Checkout repo
1. Set up Python 3.12
1. Install `requests`
1. Run `scripts/notion_to_md.py` with `NOTION_API_TOKEN` from GitHub Secrets
1. Commit all changed files with `[skip ci]` to prevent infinite loops
**The Python script handles:**
- Reading page mappings (page IDs, output paths)
- Fetching all blocks per page with pagination (`has_more` / `next_cursor`)
- Converting Notion blocks to clean markdown
- Writing `.md` files to the correct repo paths
- Block types: headings, paragraphs, lists, to-dos, code blocks, quotes, dividers, callouts, images, bookmarks, tables, toggles, child pages, child databases
**Adds header:** `\<!-- Auto-generated from Notion. Do not edit directly. --\>`
**Commit identity:**
```plain text
notion-mirror[bot] <notion-mirror[bot]@users.noreply.github.com>
```
---
## Status Writeback
**Open question:** v1 had Module 11 writing Mirror Status and Last Mirrored back to Export Scope Mapping via Notion API. In v2, options:
- **Option A:** Python script writes status back after each successful page conversion
- **Option B:** Separate Make scenario triggered by Action completion (via webhook)
- **Option C:** Manual — check repo commit history
*Document which approach is implemented here once decided.*
---
## Testing Plan
1. Trigger via GitHub UI (`workflow_dispatch`) — verify Action runs and `.md` files appear
1. Trigger via Make webhook — verify `repository_dispatch` fires the Action
1. Spot-check markdown quality against Notion source
1. Verify large pages (>100 blocks) are fully converted
1. Verify single atomic commit (not per-page)
---
## Export Scope Mapping — Column Relevance (v2)
| **Column** | **Still Needed?** | **Notes** |
| --- | --- | --- |
| Page Name | Yes | Human-readable identifier |
| Active | Yes | Controls which pages are mirrored |
| Path | Yes | Canonical `.md` output path — Python script reads this |
| Source Page | Yes | Python script extracts page ID from this URL |
| Section | Yes | Grouping and filtering |
| Mirror Status | Depends | Only if status writeback is implemented (see above) |
| Last Mirrored | Depends | Only if status writeback is implemented |
| JSON Path | **No** | v1 artifact — Make no longer commits JSON to `_raw/`. Can be removed or retained as documentation. |
---
## Retired v1 Modules
The following modules existed in v1 and have been removed. Documented here for historical reference:
| **v1 #** | **Name** | **Why Removed** |
| --- | --- | --- |
| 3 | Parse Response | Make no longer processes Notion data |
| 4 | Split Rows (Iterator) | No per-page loop in Make |
| 5 | Extract Row Data | No variable extraction needed |
| 6 | Fetch Blocks | Moved to Python script (with pagination) |
| 7 | Get File SHA | Eliminated — single atomic commit via git CLI |
| 8 | Resume (error handler) | No SHA lookup to error-handle |
| 9 | Build Commit Payload | Eliminated — no base64 encoding needed |
| 10 | Commit to GitHub | Eliminated — git CLI in Action handles commits atomically |
| 11 | Write Status Back | Moved to Python script or deferred (see Status Writeback) |
