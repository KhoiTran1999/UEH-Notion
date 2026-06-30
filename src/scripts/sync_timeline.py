"""
Sync In Progress tasks into 'All Tasks Timeline' page.

Fetches all In Progress tasks from DB, parses their content blocks,
detects strikethrough (completed) and @date mentions (deadline),
sorts by earliest deadline, and writes to the timeline page.
"""
import httpx
import time
import re
from datetime import datetime
from src.config.settings import Config
from src.utils.logger import logger
from src.utils.block_parser import parse_block, fetch_blocks_recursive, blocks_to_notion_api_blocks


class TimelineSyncer:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {Config.NOTION_TOKEN}",
            "Notion-Version": Config.NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self.base_url = "https://api.notion.com/v1"

    def _resolve_db_info(self, client, container_id):
        resp = client.get(f"{self.base_url}/databases/{container_id}", headers=self.headers)
        if resp.status_code != 200:
            logger.error(f"Container error: {resp.status_code} - {resp.text}")
            return None
        db_info = resp.json()
        data_sources = db_info.get("data_sources", [])
        return data_sources[0]["id"] if data_sources else container_id

    def fetch_in_progress_tasks(self):
        """Query DB for tasks with status 'In progress'."""
        container_id = Config.NOTION_DB_TASK
        if not container_id:
            return []

        with httpx.Client(timeout=30.0) as client:
            source_id = self._resolve_db_info(client, container_id)
            if not source_id:
                return []

            url = f"{self.base_url}/data_sources/{source_id}/query"
            resp = client.post(url, headers=self.headers, json={
                "filter": {"property": "Trạng thái", "status": {"equals": "In progress"}},
                "page_size": 100,
            })
            if resp.status_code != 200:
                logger.error(f"Query error: {resp.status_code} - {resp.text}")
                return []

            tasks = []
            for page in resp.json().get("results", []):
                props = page.get("properties", {})
                name_arr = props.get("Name", {}).get("title", [])
                name = name_arr[0]["plain_text"] if name_arr else ""
                if not name or name == "All Tasks Timeline":
                    continue
                tasks.append({"page_id": page["id"], "name": name})

            logger.info(f"Fetched {len(tasks)} In Progress tasks")
            return tasks

    def _extract_deadline_from_text(self, text):
        """Find @date pattern in text or dates like YYYY-MM-DD."""
        m = re.search(r'(\d{4}-\d{2}-\d{2})', text)
        if m:
            return m.group(1)
        return None

    def _find_earliest_deadline(self, parsed_blocks):
        """Find the earliest non-strikethrough deadline from parsed blocks."""
        dates = []
        for pb in parsed_blocks:
            if pb["completed"]:
                continue
            if pb["deadline"]:
                dates.append(pb["deadline"])
        if not dates:
            return None
        return min(dates)

    def run(self):
        logger.info("Starting timeline sync...")

        timeline_page_id = self.find_timeline_page()
        if not timeline_page_id:
            logger.error("'All Tasks Timeline' page not found")
            return False
        logger.info(f"Found timeline page: {timeline_page_id}")

        tasks = self.fetch_in_progress_tasks()
        if not tasks:
            logger.warning("No In Progress tasks found")
            return False

        # Fetch content + parse blocks for each task
        enriched_tasks = []
        with httpx.Client(timeout=60.0) as client:
            for task in tasks:
                logger.info(f"Parsing: {task['name']}")
                raw = fetch_blocks_recursive(client, self.headers, task["page_id"])
                parsed = []
                for item in raw:
                    pb = parse_block(item["block"])
                    if pb:
                        pb["depth"] = item.get("depth", 0)
                        parsed.append(pb)
                task["parsed_blocks"] = parsed
                task["deadline"] = self._find_earliest_deadline(parsed)
                enriched_tasks.append(task)
                time.sleep(0.2)

        # Sort by earliest deadline (no-deadline last)
        def sort_key(t):
            return t["deadline"] or "9999-99-99"
        enriched_tasks.sort(key=sort_key)

        for t in enriched_tasks:
            dl = t["deadline"] or "No deadline"
            logger.info(f"  {t['name']} -> {dl}")

        # Build Notion API blocks for timeline page
        page_blocks = []

        # Header callout
        page_blocks.append({
            "object": "block", "type": "callout",
            "callout": {
                "icon": {"type": "emoji", "emoji": "🔄"},
                "rich_text": [{"type": "text", "text": {"content":
                    f"Cập nhật: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {len(enriched_tasks)} tasks"}}],
            },
        })
        page_blocks.append({"object": "block", "type": "divider", "divider": {}})

        for task in enriched_tasks:
            # Task heading
            page_blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": f"📌 {task['name']}"}}]
                },
            })

            # Deadline line
            if task["deadline"]:
                try:
                    dt = datetime.fromisoformat(task["deadline"])
                    label = dt.strftime("%A, %d %B %Y")
                except:
                    label = task["deadline"]
                page_blocks.append({
                    "object": "block", "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": f"📅 {label}"}}]
                    },
                })

            # Notion-format blocks from task content
            task_blocks = blocks_to_notion_api_blocks(task["parsed_blocks"], task["name"])
            page_blocks.extend(task_blocks)

            # Count completed
            n_completed = sum(1 for pb in task["parsed_blocks"] if pb["completed"])
            if n_completed:
                page_blocks.append({
                    "object": "block", "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content":
                            f"✅ {n_completed} mục đã hoàn thành"}}]
                    },
                })

            page_blocks.append({"object": "block", "type": "divider", "divider": {}})

        logger.info(f"Clearing old timeline content...")
        self.clear_page_children(timeline_page_id)

        logger.info(f"Writing {len(page_blocks)} blocks...")
        self.append_blocks_to_page(timeline_page_id, page_blocks)

        logger.info("Timeline sync complete!")
        return True

    def fetch_page_blocks(self, page_id):
        blocks = []
        cursor = None
        with httpx.Client(timeout=30.0) as client:
            while True:
                url = f"{self.base_url}/blocks/{page_id}/children"
                params = {"page_size": 100}
                if cursor:
                    params["start_cursor"] = cursor
                resp = client.get(url, headers=self.headers, params=params)
                if resp.status_code != 200:
                    break
                data = resp.json()
                blocks.extend(data.get("results", []))
                if not data.get("has_more"):
                    break
                cursor = data.get("next_cursor")
        return blocks

    def find_timeline_page(self):
        container_id = Config.NOTION_DB_TASK
        with httpx.Client(timeout=30.0) as client:
            source_id = self._resolve_db_info(client, container_id)
            if not source_id:
                return None
            url = f"{self.base_url}/data_sources/{source_id}/query"
            resp = client.post(url, headers=self.headers, json={
                "filter": {"property": "Name", "title": {"equals": "All Tasks Timeline"}},
            })
            if resp.status_code != 200:
                return None
            results = resp.json().get("results", [])
            return results[0]["id"] if results else None

    def clear_page_children(self, page_id):
        blocks = self.fetch_page_blocks(page_id)
        if not blocks:
            return
        with httpx.Client(timeout=30.0) as client:
            for block in blocks:
                resp = client.delete(f"{self.base_url}/blocks/{block['id']}", headers=self.headers)
                if resp.status_code != 200:
                    logger.warning(f"Delete error: {resp.status_code}")
                time.sleep(0.1)

    def append_blocks_to_page(self, page_id, blocks_payload):
        url = f"{self.base_url}/blocks/{page_id}/children"
        for i in range(0, len(blocks_payload), 100):
            chunk = blocks_payload[i:i+100]
            with httpx.Client(timeout=30.0) as client:
                resp = client.patch(url, headers=self.headers, json={"children": chunk})
                if resp.status_code != 200:
                    logger.error(f"Append error: {resp.status_code} - {resp.text}")
                time.sleep(0.3)


def run():
    syncer = TimelineSyncer()
    return syncer.run()


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    run()
