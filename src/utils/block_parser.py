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
            parts.append(t)
            clean_parts.append(t)

            # Extract @date mentions
            mention = item.get("mention", {})
            if mention.get("type") == "date":
                d = mention.get("date", {}).get("start")
                if d:
                    dates.append(d)

    return "".join(parts), "".join(clean_parts), dates, all_struck


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


def parse_all_blocks(blocks):
    """Parse a flat list of block dicts (each with 'block' and 'depth' keys).
    Returns list of parsed block dicts.
    """
    parsed = []
    prev_deadline = None
    for item in blocks:
        b = item["block"]
        depth = item.get("depth", 0)
        indent = "  " * depth
        result = parse_block(b, parent_date=prev_deadline)
        if result:
            # Track last seen deadline for child blocks without dates
            if result["deadline"]:
                prev_deadline = result["deadline"]
            if indent and result["type"] not in ("heading_1", "heading_2", "heading_3", "divider"):
                result["text"] = indent + result["text"]
                if result["clean_text"]:
                    result["clean_text"] = indent + result["clean_text"]
            parsed.append(result)
    return parsed


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


def blocks_to_notion_api_blocks(parsed_blocks, task_name):
    """Convert parsed blocks into Notion API block objects for writing to timeline page.
    Skips completed (all-strikethrough) blocks.
    """
    notion_blocks = []
    prev_deadline = None

    for pb in parsed_blocks:
        if pb["completed"]:
            continue  # Skip completed items

        # If this block has a new deadline, write a date label block
        if pb["deadline"] and pb["deadline"] != prev_deadline:
            prev_deadline = pb["deadline"]
            try:
                dt = datetime.fromisoformat(pb["deadline"])
                label = dt.strftime("%A, %d %B %Y")
            except:
                label = pb["deadline"]
            notion_blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": f"📅 {label}"}}]
                },
            })

        # Map block type
        if pb["type"] == "divider":
            notion_blocks.append({
                "object": "block", "type": "divider", "divider": {}
            })
            continue

        clean = pb["clean_text"]
        if not clean.strip():
            continue

        # Remove prefix for rich text
        content_text = clean
        if content_text.startswith("• ") or content_text.startswith("☐ ") or content_text.startswith("☑ ") or content_text.startswith("1. "):
            content_text = content_text[2:]
        # Remove heading prefixes
        content_text = re.sub(r'^#{1,3} ', '', content_text)

        # Use bullet by default
        notion_blocks.append({
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": content_text}}]
            },
        })

    return notion_blocks


def format_for_telegram(parsed_blocks, task_name):
    """Format parsed blocks into a Telegram section for one task."""
    if not parsed_blocks:
        return ""

    lines = []
    pending = [p for p in parsed_blocks if not p["completed"]]
    completed = [p for p in parsed_blocks if p["completed"]]

    if not pending and not completed:
        return ""

    lines.append(f"📌 *{task_name}*")
    lines.append("")

    # Group pending by deadline
    groups = {}
    no_date = []
    for p in pending:
        d = p["deadline"] or "no_date"
        if d == "no_date":
            no_date.append(p)
        else:
            groups.setdefault(d, []).append(p)

    # Sort groups by date
    for date_key in sorted(groups.keys()):
        try:
            dt = datetime.fromisoformat(date_key)
            lines.append(f"  📅 `{dt.strftime('%d/%m')}`:")
        except:
            lines.append(f"  📅 `{date_key}`:")

        for p in groups[date_key]:
            text = p["clean_text"]
            lines.append(f"    {text}")

    if no_date:
        lines.append("  📌 Cần làm:")
        for p in no_date:
            lines.append(f"    {p['clean_text']}")

    if completed:
        lines.append(f"  ✅ *{len(completed)} mục đã hoàn thành*")

    return "\n".join(lines)
