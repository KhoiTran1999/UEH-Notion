"""Timeline service: fetch In Progress tasks, parse content, sort all deadline blocks chronologically, and append task name suffix."""
import httpx
from datetime import datetime
from src.config.settings import Config
from src.utils.logger import logger


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


def get_timeline_summary():
    """Fetch tasks, parse content, flatten all deadline blocks, sort chronologically, and format."""
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
                if pb and not pb["completed"] and pb.get("deadline"):
                    pb["task_name"] = task["name"]
                    all_deadline_blocks.append(pb)

    if not all_deadline_blocks:
        return "📭 Không có task nào có deadline."

    # Sort all blocks by deadline ascending
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

        for pb in grouped_by_date[date_key]:
            clean_text = pb["clean_text"]
            # Strip markdown prefixes like bullets or numbers to rebuild custom style
            clean_text = clean_text.strip()
            if clean_text.startswith("• "):
                clean_text = clean_text[2:]
            elif clean_text.startswith("1. "):
                clean_text = clean_text[3:]
            elif clean_text.startswith("☐ "):
                clean_text = clean_text[2:]

            clean_text = _escape_telegram_markdown(clean_text)
            task_suffix = f" - *{_escape_telegram_markdown(pb['task_name'])}*"

            lines.append(f"  • {clean_text}{task_suffix}")

        lines.append("")

    return "\n".join(lines).strip()
