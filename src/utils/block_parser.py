"""Parse Notion blocks: detect strikethrough (completed) + @date (deadline)."""
import re
from datetime import datetime


def parse_rich_text(rich_text):
    """Parse a Notion rich_text array.

    Returns:
      text: plain text content (strikethrough items replaced with ~~strikethrough~~)
      clean_text: text WITHOUT any strikethrough content
      dates: list of date strings found in non-strikethrough mentions
      all_strikethrough: True if every rich_text item has strikethrough
    """
    parts = []
    clean_parts = []
    dates = []
    all_struck = True

    for item in rich_text:
        t = item.get("plain_text", "")
        struck = item.get("annotations", {}).get("strikethrough", False)

        if struck:
            parts.append(f"~~{t}~~")
            # don't add to clean_parts
        else:
            all_struck = False
            # Extract @date mentions
            mention = item.get("mention", {})
            if mention.get("type") == "date":
                d = mention.get("date", {}).get("start")
                if d:
                    dates.append(d)
                parts.append(t)
                clean_parts.append(t)  # Keep date text for AI to parse
            else:
                parts.append(t)
                clean_parts.append(t)

    return "".join(parts), "".join(clean_parts).strip(), dates, all_struck


def parse_block(block, parent_date=None):
    """Parse a single Notion block into structured info.

    Returns dict or None if block type is unsupported/skip.
    """
    b_type = block.get("type")
    rich_text = block.get(b_type, {}).get("rich_text", []) if b_type else []
    if not rich_text:
        return None

    text, clean_text, dates, all_done = parse_rich_text(rich_text)

    if not text.strip():
        return None

    # Block type emoji prefix
    prefix = ""
    if b_type == "bulleted_list_item":
        prefix = "• "
    elif b_type == "numbered_list_item":
        prefix = "1. "
    elif b_type == "to_do":
        checked = block.get("to_do", {}).get("checked", False)
        prefix = "☑ " if checked else "☐ "
    elif b_type == "callout":
        icon = block.get("callout", {}).get("icon", {}).get("emoji", "💡")
        prefix = f"{icon} "
    elif b_type in ("heading_1", "heading_2", "heading_3"):
        level = int(b_type.split("_")[1])
        prefix = "#" * level + " "
    elif b_type == "divider":
        return {"type": "divider", "text": "---", "clean_text": "---",
                "dates": [], "completed": False, "block_type": "divider"}

    deadline = dates[0] if dates else parent_date

    return {
        "type": b_type,
        "text": f"{prefix}{text}",
        "clean_text": f"{prefix}{clean_text}" if clean_text.strip() else "",
        "dates": dates,
        "deadline": deadline,
        "completed": all_done,
        "block_type": b_type,
    }


def fetch_page_blocks(client, headers, page_id):
    """Fetch top-level blocks of a page (paginated)."""
    all_blocks = []
    cursor = None
    while True:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        params = {"page_size": 100}
        if cursor:
            params["start_cursor"] = cursor
        resp = client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            break
        data = resp.json()
        all_blocks.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return all_blocks


def fetch_blocks_recursive(client, headers, page_id):
    """Fetch all blocks including children recursively. Returns flat list."""
    all_items = []
    top_blocks = fetch_page_blocks(client, headers, page_id)
    for block in top_blocks:
        all_items.append({"block": block, "depth": 0})
        if block.get("has_children"):
            _fetch_children(client, headers, block["id"], all_items, depth=1)
    return all_items


def _fetch_children(client, headers, block_id, result_list, depth=0):
    """Recursively fetch children blocks."""
    blocks = fetch_page_blocks(client, headers, block_id)
    for block in blocks:
        result_list.append({"block": block, "depth": depth})
        if block.get("has_children"):
            _fetch_children(client, headers, block["id"], result_list, depth + 1)

