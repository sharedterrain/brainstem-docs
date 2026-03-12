#!/usr/bin/env python3
"""
notion_to_md.py

Queries the Notion "Export Scope Mapping" database for active rows,
fetches block content for each page (with full pagination),
converts to clean Markdown, and writes .md files to the repo.

Skips pages where last_edited_time has not changed since Last Mirrored,
UNLESS:
  - Last Mirrored Visibility differs from current VISIBILITY (visibility
    change detection), OR
  - Mirror Status == "Stale" (manual force-convert trigger)

In either force case, the page is re-converted regardless of timestamp.
Stale copy cleanup in the old repo is a manual step.

Writes Mirror Status, Last Mirrored, and Last Mirrored Visibility back to
each mapping row on completion. Staleness flagging is handled separately
by check_staleness.py.

Per-page errors are caught and reported without aborting the run. All
successfully converted pages are written and committed. Script exits 1
only if one or more pages failed.

Filters by VISIBILITY environment variable:
  - "Public"  — process only rows where Visibility = Public
  - "Private" — process only rows where Visibility = Private

Required env vars:
  NOTION_API_TOKEN          — Notion integration token
  NOTION_EXPORT_SCOPE_DB_ID — optional override; defaults to known DB ID
  VISIBILITY                — "Public" or "Private" (required, no default)
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

VISIBILITY = os.environ.get("VISIBILITY")
if VISIBILITY not in ("Public", "Private"):
    print('ERROR: VISIBILITY must be set to "Public" or "Private".', file=sys.stderr)
    sys.exit(1)

NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

REPO_ROOT = Path(__file__).parent.parent


# ── Export Scope query ────────────────────────────────────────────────────────

def fetch_export_scope() -> list:
    """Query the Export Scope Mapping DB for active rows matching VISIBILITY."""
    url = f"https://api.notion.com/v1/databases/{EXPORT_SCOPE_DB_ID}/query"
    payload = {
        "filter": {
            "and": [
                {"property": "Active", "checkbox": {"equals": True}},
                {"property": "Visibility", "select": {"equals": VISIBILITY}},
            ]
        }
    }
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

            last_mirrored = (props.get("Last Mirrored", {}).get("date") or {}).get("start", "")

            last_mirrored_visibility = (
                (props.get("Last Mirrored Visibility", {}).get("select") or {}).get("name", "")
            )

            mirror_status = (
                (props.get("Mirror Status", {}).get("select") or {}).get("name", "")
            )

            if not page_id or not path:
                print(f"  SKIP — missing page_id or path for row: {name!r}")
                continue

            pages.append({
                "name": name,
                "page_id": page_id,
                "path": path,
                "row_id": row["id"],
                "last_mirrored": last_mirrored,
                "last_mirrored_visibility": last_mirrored_visibility,
                "mirror_status": mirror_status,
            })

        if data.get("has_more"):
            payload["start_cursor"] = data["next_cursor"]
        else:
            break

    return pages


# ── Notion API helpers ────────────────────────────────────────────────────────

def update_mirror_status(row_id: str, status: str) -> None:
    """Write Mirror Status, Last Mirrored, and Last Mirrored Visibility to the ESM row."""
    url = f"https://api.notion.com/v1/pages/{row_id}"
    payload = {
        "properties": {
            "Mirror Status": {"select": {"name": status}},
            "Last Mirrored": {"date": {"start": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}},
            "Last Mirrored Visibility": {"select": {"name": VISIBILITY}},
        }
    }
    requests.patch(url, headers=HEADERS, json=payload)


def fetch_page_metadata(page_id: str) -> dict:
    """Fetch page title and last_edited_time."""
    url = f"https://api.notion.com/v1/pages/{page_id}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()

    props = data.get("properties", {})
    title = page_id
    for prop in props.values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            title = "".join(p.get("plain_text", "") for p in parts)
            break

    last_edited = data.get("last_edited_time", "")
    return {"title": title, "last_edited_time": last_edited}


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
    children_handled = False

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
        children_handled = True
    elif btype == "numbered_list_item":
        lines.append(f"{indent}1. {rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            lines.append(block_to_md(child, depth + 1))
        children_handled = True
    elif btype == "to_do":
        checked = "x" if data.get("checked") else " "
        lines.append(f"{indent}- [{checked}] {rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            lines.append(block_to_md(child, depth + 1))
        children_handled = True
    elif btype == "toggle":
        text = rich_text_to_md(data.get("rich_text", []))
        lines.append(f"{indent}<details><summary>{text}</summary>")
        lines.append("")
        for child in children:
            lines.append(block_to_md(child, depth + 1))
        lines.append("")
        lines.append(f"{indent}</details>")
        children_handled = True
    elif btype == "quote":
        lines.append(f"> {rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            for line in block_to_md(child, 0).splitlines():
                lines.append(f"> {line}")
        children_handled = True
    elif btype == "callout":
        icon = ""
        icon_data = data.get("icon", {})
        if icon_data.get("type") == "emoji":
            icon = icon_data.get("emoji", "") + " "
        lines.append(f"> {icon}{rich_text_to_md(data.get('rich_text', []))}")
        for child in children:
            for line in block_to_md(child, 0).splitlines():
                lines.append(f"> {line}")
        children_handled = True
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
        children_handled = True
    elif btype == "table_row":
        children_handled = True
    elif btype == "image":
        url = (data.get("external") or data.get("file") or {}).get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        lines.append(f"![{caption or 'image'}]({url})")
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
        children_handled = True
    elif btype == "breadcrumb":
        lines.append("<!-- breadcrumb -->")
    elif btype == "template":
        lines.append(f"<!-- template: {rich_text_to_md(data.get('rich_text', []))} -->")
    elif btype == "equation":
        lines.append(f"$${data.get('expression', '')}$$")
    else:
        lines.append(f"<!-- unsupported block type: {btype} -->")

    # Fallback: recurse into children for any block type that hasn't already handled them
    if not children_handled and children:
        for child in children:
            lines.append(block_to_md(child, depth))

    return "\n".join(lines)


def blocks_to_md(blocks: list) -> str:
    sections = [block_to_md(b) for b in blocks]
    raw = "\n\n".join(sections)
    return re.sub(r"\n{3,}", "\n\n", raw).strip() + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Querying Export Scope Mapping DB (Visibility={VISIBILITY})...")
    pages = fetch_export_scope()

    if not pages:
        print(f"No active {VISIBILITY} pages found — nothing to convert.")
        return

    print(f"Found {len(pages)} active {VISIBILITY} pages...")
    errors = []
    skipped = 0
    converted = 0

    for entry in pages:
        page_id = entry["page_id"]
        path = entry["path"]
        name = entry["name"]
        row_id = entry["row_id"]
        last_mirrored = entry["last_mirrored"]
        last_mirrored_visibility = entry["last_mirrored_visibility"]
        mirror_status = entry["mirror_status"]
        print(f"  → {name}  ({path})")

        try:
            metadata = fetch_page_metadata(page_id)
            last_edited = metadata["last_edited_time"]
            title = metadata["title"]

            # Detect Visibility change — force conversion if Visibility has changed
            # since last mirror, regardless of content timestamp.
            visibility_changed = (
                last_mirrored_visibility != ""
                and last_mirrored_visibility != VISIBILITY
            )

            # Detect manual Stale flag — force conversion regardless of timestamp.
            stale_forced = mirror_status == "Stale"

            if visibility_changed:
                print(f"     ⚠ Visibility changed ({last_mirrored_visibility} → {VISIBILITY}) — forcing conversion")
            elif stale_forced:
                print(f"     ⚠ Mirror Status = Stale — forcing conversion")
            elif last_mirrored and last_edited <= last_mirrored:
                print(f"     ↩ unchanged — skipping")
                skipped += 1
                continue

            blocks = fetch_blocks(page_id)
            md_content = f"# {title}\n\n{blocks_to_md(blocks)}"

            out_path = REPO_ROOT / path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md_content, encoding="utf-8")
            print(f"     ✓ {out_path.relative_to(REPO_ROOT)}")
            update_mirror_status(row_id, "Current")
            converted += 1

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

    print(f"\nDone — {converted} converted, {skipped} unchanged, {len(errors)} failed.")

    if errors:
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
