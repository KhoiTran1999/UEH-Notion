"""Timeline service: fetch In Progress tasks, parse content, send raw blocks to AI for intelligent analysis."""
import httpx
from datetime import datetime, timezone, timedelta
from src.config.settings import Config
from src.utils.logger import logger
from src.services.ai import AIService

def _resolve_date_shortcuts(raw_text):
    """Replace @Today, @Tomorrow, @Monday (or @ThứHai) in raw_text with concrete dd/mm dates."""
    if not raw_text:
        return raw_text
    date_format = "%d/%m %H:%M"

    # Helper to resolve weekday
    def resolve_day(short_day):
        # Normalize input
        if short_day.startswith("@"):
            day = short_day[1:]
        else:
            day = short_day

        # Weekdays in both English and Vietnamese
        weekday_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6,
            "ThứHai": 0, "ThứBa": 1, "ThứTư": 2, "ThứNăm": 3, "ThứSáu": 4, "ThứBảy": 5, "Chủ nhật": 6,
        }
        if day in weekday_map:
            idx = weekday_map[day]
            now = datetime.now(timezone(timedelta(hours=7)))
            current_weekday = now.weekday()
            days_ahead = idx - current_weekday
            if days_ahead <= 0:
                days_ahead += 7
            target_date = now + timedelta(days=days_ahead)
            return target_date.strftime(date_format)
        return None

    result = raw_text

    # @Today /
    today_str = datetime.now(timezone(timedelta(hours=7))).strftime("%d/%m %H:%M")
    result = result.replace("@Today", today_str)

    # @Tomorrow
    tomorrow = datetime.now(timezone(timedelta(hours=7))) + timedelta(days=1)
    result = result.replace("@Tomorrow", tomorrow.strftime(date_format))

    # @Weekday patterns
    for pattern in ["@Monday", "@Tuesday", "@Wednesday", "@Thursday", "@Friday", "@Saturday", "@Sunday",
                    "@ThứHai", "@ThứBa", "@ThứTư", "@ThứNăm", "@ThứSáu", "@ThứBảy", "@Chủ nhật"]:
        resolved = resolve_day(pattern)
        if resolved:
            result = result.replace(pattern, resolved)

    import re

    # Replace ISO datetimes from Notion mentions (e.g. 2026-07-01T09:00:00.000+07:00 or 2026-07-01) with DD/MM HH:MM
    def _iso_replacer(match):
        date_str = match.group(1)
        try:
            # Handle full ISO format with timezone
            if "T" in date_str:
                dt = datetime.fromisoformat(date_str)
                return dt.strftime("%d/%m %H:%M")
            # Handle date only
            else:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt.strftime("%d/%m")
        except ValueError:
            return date_str

    # Regex to catch Notion ISO formats like 2026-07-01T09:00:00.000+07:00 or 2026-07-01
    iso_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:[+-]\d{2}:\d{2}|Z)?)?)')
    result = iso_pattern.sub(_iso_replacer, result)

    return result


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
    """Return list of In Progress tasks."""
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


def get_timeline_summary():
    """Fetch tasks, gather raw non-completed blocks, send to AI for analysis."""
    from src.utils.block_parser import fetch_blocks_recursive, parse_block

    tasks = fetch_in_progress_tasks()
    if not tasks:
        return "📭 Không có task nào đang thực hiện."

    # Gather raw blocks per task
    task_texts = []
    with httpx.Client(timeout=60.0) as client:
        headers = {
            "Authorization": f"Bearer {Config.NOTION_TOKEN}",
            "Notion-Version": Config.NOTION_VERSION,
        }
        for task in tasks:
            raw = fetch_blocks_recursive(client, headers, task["page_id"])
            lines = []
            for item in raw:
                pb = parse_block(item["block"])
                if pb and not pb["completed"]:
                    text = pb.get("clean_text", "").strip()
                    if text:
                        lines.append(text)
            if lines:
                task_texts.append({
                    "task_name": task["name"],
                    "blocks": lines
                })

    if not task_texts:
        return "📭 Không có task nào có nội dung."

    # Send to AI for full analysis
    raw_data = "\n\n".join(
        f"## {t['task_name']}\n" + "\n".join(f"- {b}" for b in t["blocks"])
        for t in task_texts
    )

    # Preprocess @date shortcuts -> actual dd/mm dates
    raw_data = _resolve_date_shortcuts(raw_data)

    ai_summary = AIService().summarize_timeline(raw_data, is_raw_text=True)

    return ai_summary
