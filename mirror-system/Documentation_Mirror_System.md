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

10 child pages covering mirror publishing rules, drift control, CI checks, automation config, contract templates, bootstrap guide, and protocol files. Written for the full automated system — pick up when MVP is proven.

**Child page:** 📁 Projects

Brain Stem mirror mapping and project-specific mirror config. The export scope mapping in Phase 1 covers this need for now.

**Child database:** Friction Log

**Child database:** Export Scope Mapping https://hook.us2.make.com/mjpxw1t8bt5p0d43tv97yt42v17r6jp3— fires Make webhook → repository_dispatch → GitHub Action → converts and commits all active pages

**Child page:** Make Scenario Build Reference
