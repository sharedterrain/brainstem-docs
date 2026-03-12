#!/usr/bin/env python3
"""
check_staleness.py

Two jobs in one script:
1. Resolve empty Source Page URLs by searching the Notion API by title
2. Fetch last_edited_time for each source page and write it to "Last Updated"

Staleness rule: if Last Updated > Last Mirrored, the doc
has been edited since its last mirror run.

Visibility rule: if Last Mirrored Visibility != Visibility (and Last Mirrored
Visibility is non-empty), the row is marked Stale regardless of edit time.
This flags rows where visibility changed since last mirror — a reminder that
cleanup (e.g. deleting the stale copy from the old repo) may be needed.

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
    """Query the Export Scope Mapping DB for all active rows."""
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
            last_mirrored = (props.get("Last Mirrored", {}).get("date") or {}).get("start", "")
            visibility = (props.get("Visibility", {}).get("select") or {}).get("name", "")
            last_mirrored_visibility = (props.get("Last Mirrored Visibility", {}).get("select") or {}).get("name", "")

            rows.append({
                "name": name,
                "source_url": source_url,
                "last_mirrored": last_mirrored,
                "visibility": visibility,
                "last_mirrored_visibility": last_mirrored_visibility,
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
    """Search Notion for a page matching the given title exactly."""
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
    payload = {"properties": {"Source Page": {"url": page_url}}}
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
    url = f"https://api.notion.com/v1/pages/{row_id}"
    payload = {"properties": {"Last Updated": {"date": {"start": last_edited}}}}
    r = requests.patch(url, headers=HEADERS, json=payload)
    r.raise_for_status()


def write_mirror_status(row_id: str, status: str) -> None:
    """Write Mirror Status to the Export Scope Mapping row."""
    url = f"https://api.notion.com/v1/pages/{row_id}"
    payload = {"properties": {"Mirror Status": {"select": {"name": status}}}}
    r = requests.patch(url, headers=HEADERS, json=payload)
    r.raise_for_status()


def write_cleanup_flag(row_id: str) -> None:
    """Check the Cleanup checkbox on the Export Scope Mapping row."""
    url = f"https://api.notion.com/v1/pages/{row_id}"
    payload = {"properties": {"Cleanup": {"checkbox": True}}}
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
            # ── Visibility mismatch check (takes priority) ────────────────
            lmv = row["last_mirrored_visibility"]
            vis = row["visibility"]
            if lmv and lmv != vis:
                write_mirror_status(row_id, "Stale")
                write_cleanup_flag(row_id)
                print(f"  ⚠ {name} — visibility changed ({lmv} → {vis}) → STALE (cleanup needed)")
                continue

            # ── Edit-time staleness check ─────────────────────────────────
            last_edited = fetch_last_edited_time(page_id)
            if not last_edited:
                print(f"  SKIP — no last_edited_time for: {name!r}")
                continue

            write_last_updated(row_id, last_edited)

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
