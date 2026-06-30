"""Timeline service: fetch In Progress tasks, parse content, send raw blocks to AI for intelligent analysis."""
import httpx
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

    ai_summary = AIService().summarize_timeline(raw_data, is_raw_text=True)

    return ai_summary
