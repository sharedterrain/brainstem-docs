#!/usr/bin/env python3
"""
Notion block JSON → Markdown converter.
Reads a list of changed _raw/**/*.json files and writes .md files
at the corresponding path (stripped of _raw/ prefix).

Usage: python convert.py changed_files.txt
"""

import json
import os
import sys

HEADER = "<!-- Auto-generated from Notion. Do not edit directly. -->\n\n"


def block_to_md(block, depth=0):
    """Convert a single Notion block to markdown string."""
    btype = block.get("type", "")
    data = block.get(btype, {})
    rich = data.get("rich_text", [])
    text = rich_text_to_md(rich)
    children_md = ""

    # Recurse into children if present
    if block.get("has_children") and "children" in block:
        child_lines = []
        for child in block["children"]:
            child_lines.append(block_to_md(child, depth + 1))
        children_md = "\n".join(child_lines)

    indent = "  " * depth

    if btype == "paragraph":
        return f"{indent}{text}\n" if text else ""

    elif btype in ("heading_1", "heading_2", "heading_3"):
        level = {"heading_1": "#", "heading_2": "##", "heading_3": "###"}[btype]
        return f"{level} {text}\n"

    elif btype == "bulleted_list_item":
        result = f"{indent}- {text}\n"
        if children_md:
            result += children_md
        return result

    elif btype == "numbered_list_item":
        result = f"{indent}1. {text}\n"
        if children_md:
            result += children_md
        return result

    elif btype == "to_do":
        checked = data.get("checked", False)
        box = "[x]" if checked else "[ ]"
        return f"{indent}- {box} {text}\n"

    elif btype == "toggle":
        result = f"{indent}<details>\n{indent}<summary>{text}</summary>\n\n"
        if children_md:
            result += children_md
        result += f"\n{indent}</details>\n"
        return result

    elif btype == "code":
        lang = data.get("language", "")
        return f"```{lang}\n{text}\n```\n"

    elif btype == "quote":
        lines = text.split("\n")
        return "\n".join(f"> {l}" for l in lines) + "\n"

    elif btype == "callout":
        icon = ""
        if data.get("icon"):
            icon_data = data["icon"]
            if icon_data.get("type") == "emoji":
                icon = icon_data.get("emoji", "") + " "
        return f"> {icon}{text}\n"

    elif btype == "divider":
        return "---\n"

    elif btype == "image":
        src = ""
        img_type = data.get("type", "")
        if img_type == "external":
            src = data.get("external", {}).get("url", "")
        elif img_type == "file":
            src = data.get("file", {}).get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        alt = caption or "image"
        return f"![{alt}]({src})\n"

    elif btype == "bookmark":
        url = data.get("url", "")
        caption = rich_text_to_md(data.get("caption", []))
        label = caption or url
        return f"[{label}]({url})\n"

    elif btype == "table":
        # Table rows are children
        if children_md:
            return children_md
        return ""

    elif btype == "table_row":
        cells = data.get("cells", [])
        row_parts = [rich_text_to_md(cell) for cell in cells]
        return "| " + " | ".join(row_parts) + " |\n"

    elif btype == "child_page":
        title = data.get("title", "")
        return f"**[{title}]**\n"

    elif btype == "child_database":
        title = data.get("title", "")
        return f"**[Database: {title}]**\n"

    elif btype == "column_list":
        if children_md:
            return children_md
        return ""

    elif btype == "column":
        if children_md:
            return children_md
        return ""

    else:
        # Fallback: render text if available
        if text:
            return f"{text}\n"
        return ""


def rich_text_to_md(rich_text):
    """Convert Notion rich_text array to markdown string."""
    result = ""
    for rt in rich_text:
        content = rt.get("plain_text", "")
        annotations = rt.get("annotations", {})
        href = rt.get("href")

        if annotations.get("code"):
            content = f"`{content}`"
        if annotations.get("bold"):
            content = f"**{content}**"
        if annotations.get("italic"):
            content = f"*{content}*"
        if annotations.get("strikethrough"):
            content = f"~~{content}~~"
        if href:
            content = f"[{content}]({href})"

        result += content
    return result


def blocks_to_md(blocks):
    """Convert list of blocks to full markdown document."""
    lines = [HEADER]
    prev_type = None

    for block in blocks:
        btype = block.get("type", "")
        # Add spacing between different block types
        if prev_type and prev_type != btype and btype not in (
            "bulleted_list_item", "numbered_list_item", "to_do"
        ):
            lines.append("")
        lines.append(block_to_md(block))
        prev_type = btype

    return "\n".join(lines).strip() + "\n"


def convert_file(json_path):
    """Convert a single _raw/*.json file to its .md counterpart."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    blocks = data.get("results", [])
    markdown = blocks_to_md(blocks)

    # Derive output path: _raw/foo/bar.json → foo/bar.md
    rel = json_path
    if rel.startswith("_raw/"):
        rel = rel[len("_raw/"):]
    md_path = os.path.splitext(rel)[0] + ".md"

    os.makedirs(os.path.dirname(md_path) or ".", exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Converted: {json_path} → {md_path}")


def main():
    if len(sys.argv) < 2:
        print("Usage: convert.py <changed_files.txt>")
        sys.exit(1)

    changed_list = sys.argv[1]
    with open(changed_list, "r") as f:
        files = [l.strip() for l in f if l.strip().endswith(".json")]

    if not files:
        print("No JSON files to convert.")
        return

    for path in files:
        if os.path.exists(path):
            convert_file(path)
        else:
            print(f"Skipped (not found): {path}")


if __name__ == "__main__":
    main()
