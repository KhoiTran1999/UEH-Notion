"""Timeline service: fetch In Progress tasks, parse content, flatten all deadline blocks, sort chronologically, and append task name suffix. Handles duplicate deadlines on same day."""
import httpx
import re
from datetime import datetime
from src.config.settings import Config
from src.utils.logger import logger
from src.services.ai import AIService


def _get_source_id(client, container_id):
    resp = client.get(
        f"https://api.notion.com/v1/databases/{container_id}",
        headers={"Authorization": f"Bearer {Config.NOTION_TOKEN}", "Notion-Version": Config.NOTION_VERSION},
    )
    if resp.status_code != 200:
        return None
    data = resp.json()
    sources = data.get("data_sources", [])
    return sources[0]["id"] if sources else container_id


def fetch_in_progress_tasks():
    """Return sorted list of In Progress tasks."""
    container_id = Config.NOTION_DB_TASK
    if not container_id:
        return []

    headers = {
        "Authorization": f"Bearer {Config.NOTION_TOKEN}",
        "Notion-Version": Config.NOTION_VERSION,
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        source_id = _get_source_id(client, container_id)
        if not source_id:
            return []

        resp = client.post(
            f"https://api.notion.com/v1/data_sources/{source_id}/query",
            headers=headers,
            json={
                "filter": {"property": "Trạng thái", "status": {"equals": "In progress"}},
                "page_size": 100,
            },
        )
        if resp.status_code != 200:
            return []

        tasks = []
        for page in resp.json().get("results", []):
            props = page.get("properties", {})
            name_arr = props.get("Name", {}).get("title", [])
            name = name_arr[0]["plain_text"] if name_arr else ""
            if not name or name == "All Tasks Timeline":
                continue
            tasks.append({"page_id": page["id"], "name": name})
        return tasks


def _escape_telegram_markdown(text):
    if not text:
        return text
    text = text.replace('*', '＊').replace('_', '＿').replace('`', '‵').replace('[', '［')
    return text


def normalize_date(d_str):
    """Normalize date strings like YYYY-MM-DDTHH:MM:SS to YYYY-MM-DD."""
    if d_str and len(d_str) >= 10:
        if re.match(r'^\d{4}-\d{2}-\d{2}', d_str):
            return d_str[:10]
    return d_str


def get_timeline_summary():
    """Fetch tasks, parse content, flatten all deadline blocks, sort, and format (deduplicating same-day tasks)."""
    from src.utils.block_parser import fetch_blocks_recursive, parse_block

    tasks = fetch_in_progress_tasks()
    if not tasks:
        return "📭 Không có task nào đang thực hiện."

    # Fetch + parse all task content
    all_deadline_blocks = []
    with httpx.Client(timeout=60.0) as client:
        headers = {
            "Authorization": f"Bearer {Config.NOTION_TOKEN}",
            "Notion-Version": Config.NOTION_VERSION,
        }
        for task in tasks:
            raw = fetch_blocks_recursive(client, headers, task["page_id"])
            for item in raw:
                pb = parse_block(item["block"])
                if pb and not pb["completed"]:
                    # Extract raw dates
                    block_dates = pb.get("dates", [])
                    if not block_dates and pb.get("deadline"):
                        block_dates = [pb["deadline"]]

                    # Normalize and keep unique dates for this block
                    unique_dates = sorted(list(set(normalize_date(d) for d in block_dates if d)))

                    for d in unique_dates:
                        block_copy = dict(pb)
                        block_copy["deadline"] = d
                        block_copy["task_name"] = task["name"]
                        all_deadline_blocks.append(block_copy)

    if not all_deadline_blocks:
        return "📭 Không có task nào có deadline."

    # Sort all blocks by normalized deadline date ascending
    all_deadline_blocks.sort(key=lambda b: b["deadline"])

    # Group by deadline date
    grouped_by_date = {}
    for pb in all_deadline_blocks:
        date_key = pb["deadline"]
        grouped_by_date.setdefault(date_key, []).append(pb)

    # Build Telegram message
    lines = ["📅 *TIMELINE — Deadline hiện có*\n"]

    for date_key in sorted(grouped_by_date.keys()):
        try:
            dt = datetime.fromisoformat(date_key)
            label = dt.strftime("%d/%m")
            lines.append(f"📅 *{label}*:")
        except:
            lines.append(f"📅 *{date_key}*:")

        # Deduplicate tasks in the same date group by (clean_text, task_name)
        seen_tasks = set()
        for pb in grouped_by_date[date_key]:
            clean_text = pb["clean_text"].strip()
            if clean_text.startswith("• "):
                clean_text = clean_text[2:]
            elif clean_text.startswith("1. "):
                clean_text = clean_text[3:]
            elif clean_text.startswith("☐ "):
                clean_text = clean_text[2:]

            task_name = pb["task_name"]
            unique_key = (clean_text, task_name)

            if unique_key in seen_tasks:
                continue
            seen_tasks.add(unique_key)

            clean_text_esc = _escape_telegram_markdown(clean_text)
            task_suffix = f" - *{_escape_telegram_markdown(task_name)}*"

            lines.append(f"  • {clean_text_esc}{task_suffix}")

        lines.append("")

    # Get AI summary via MODEL_BRAIN
    ai_summary = AIService().summarize_timeline(all_deadline_blocks)

    return "\n".join(lines).strip() + "\n\n---\n" + ai_summary
