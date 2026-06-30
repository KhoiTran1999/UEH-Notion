"""Timeline service: fetch In Progress tasks, parse content, format for Telegram."""
import httpx
from datetime import datetime
from src.config.settings import Config
from src.utils.logger import logger
from src.utils.block_parser import (
    parse_block, fetch_blocks_recursive, fetch_page_blocks, format_for_telegram
)


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


def _find_earliest_deadline(parsed_blocks):
    dates = [pb["deadline"] for pb in parsed_blocks if not pb["completed"] and pb["deadline"]]
    return min(dates) if dates else None


def get_timeline_summary():
    """Fetch tasks, parse content, return formatted Telegram message."""
    from src.utils.block_parser import fetch_blocks_recursive, parse_block

    tasks = fetch_in_progress_tasks()
    if not tasks:
        return "📭 Không có task nào đang thực hiện."

    today = datetime.now().date()

    # Fetch + parse all task content
    enriched = []
    with httpx.Client(timeout=60.0) as client:
        headers = {
            "Authorization": f"Bearer {Config.NOTION_TOKEN}",
            "Notion-Version": Config.NOTION_VERSION,
        }
        for task in tasks:
            raw = fetch_blocks_recursive(client, headers, task["page_id"])
            parsed = []
            for item in raw:
                pb = parse_block(item["block"])
                if pb:
                    parsed.append(pb)
            task["parsed_blocks"] = parsed
            task["deadline"] = _find_earliest_deadline(parsed)
            enriched.append(task)

    # Sort by deadline (no deadline last)
    enriched.sort(key=lambda t: t["deadline"] or "9999-99-99")

    # Build Telegram message
    lines = ["📅 *TIMELINE — Tasks đang thực hiện*\n"]

    overdue = []
    urgent = []
    normal = []
    no_date = []

    for t in enriched:
        d = t["deadline"]
        if not d:
            no_date.append(t)
            continue
        try:
            dl = datetime.fromisoformat(d).date()
        except ValueError:
            no_date.append(t)
            continue
        diff = (dl - today).days
        if diff < 0:
            overdue.append((t, diff))
        elif diff <= 3:
            urgent.append((t, diff))
        else:
            normal.append((t, diff))

    def task_lines(task, diff=None):
        """Render one task's pending blocks grouped by deadline."""
        parsed = task["parsed_blocks"]
        pending = [p for p in parsed if not p["completed"]]
        completed_count = sum(1 for p in parsed if p["completed"])

        section = [f"📌 *{task['name']}*"]
        if diff is not None:
            if diff < 0:
                section.append(f"  🔴 Quá hạn {-diff} ngày!")
            elif diff == 0:
                section.append(f"  ⏰ Hôm nay!")
            elif diff <= 3:
                section.append(f"  ⏰ Còn {diff} ngày")
        section.append("")

        # Group pending blocks by deadline
        groups = {}
        no_dl = []
        for p in pending:
            dl = p.get("deadline")
            if dl:
                groups.setdefault(dl, []).append(p)
            else:
                no_dl.append(p)

        for date_key in sorted(groups.keys()):
            try:
                dt = datetime.fromisoformat(date_key)
                label = dt.strftime("%d/%m")
                section.append(f"  📅 {label}:")
            except:
                section.append(f"  📅 {date_key}:")
            for p in groups[date_key]:
                section.append(f"    {p['clean_text']}")
            section.append("")

        if no_dl:
            section.append("  📌 Cần làm:")
            for p in no_dl:
                section.append(f"    {p['clean_text']}")
            section.append("")

        if completed_count:
            section.append(f"  ✅ {completed_count} đã xong")

        return "\n".join(section)

    if overdue:
        lines.append("🔴 *QUÁ HẠN:*\n")
        for t, diff in overdue:
            lines.append(task_lines(t, diff))
            lines.append("")

    if urgent:
        lines.append("🟡 *SẮP ĐẾN HẠN:*\n")
        for t, diff in urgent:
            lines.append(task_lines(t, diff))
            lines.append("")

    if normal:
        lines.append("🟢 *ĐANG LÀM:*\n")
        for t, diff in normal:
            lines.append(task_lines(t, diff))
            lines.append("")

    if no_date:
        lines.append("⚪ *CHƯA CÓ DEADLINE:*\n")
        for t in no_date:
            lines.append(task_lines(t))
            lines.append("")

    total = len(enriched)
    warn = len(overdue) + len(urgent)
    summary = f"📊 Tổng: {total} tasks"
    if warn:
        summary += f" | ⚠️ {warn} cần ưu tiên"
    lines.append(f"---\n{summary}")

    return "\n".join(lines)
