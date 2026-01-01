import httpx
from src.config.settings import Config
from src.utils.logger import logger

class NotionService:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {Config.NOTION_TOKEN}",
            "Notion-Version": Config.NOTION_VERSION,
            "Content-Type": "application/json"
        }

    def _resolve_db_info(self, client, container_id):
        """Helper to get Real Query ID and Info from Container ID."""
        logger.info(f"🔍 Checking Container: {container_id}...")
        container_url = f"https://api.notion.com/v1/databases/{container_id}"
        
        resp = client.get(container_url, headers=self.headers)
        if resp.status_code != 200:
            logger.error(f"❌ Container Error: {resp.status_code} - {resp.text}")
            return None, {}
        
        db_info = resp.json()
        data_sources = db_info.get("data_sources", [])
        
        if not data_sources:
            return container_id, db_info
            
        real_source_id = data_sources[0]["id"]
        logger.info(f"✅ Found Data Source ID: {real_source_id}")
        return real_source_id, db_info

    def get_tasks(self):
        """Fetches tasks from the main database."""
        container_id = Config.NOTION_DATABASE_ID
        if not container_id:
            logger.error("❌ NOTION_DATABASE_ID missing")
            return []

        try:
            with httpx.Client(timeout=30.0) as client:
                real_source_id, _ = self._resolve_db_info(client, container_id)
                if not real_source_id: return []

                query_url = f"https://api.notion.com/v1/data_sources/{real_source_id}/query"
                payload = {"page_size": 100}

                logger.info("🔄 Fetching tasks...")
                response = client.post(query_url, headers=self.headers, json=payload)

                if response.status_code != 200:
                    logger.error(f"❌ Query Error: {response.status_code}")
                    return []

                results = response.json().get("results", [])
                tasks = []

                for page in results:
                    props = page.get("properties", {})
                    # ... (Mapping logic mapping same as original) ...
                    task = self._map_task_properties(props)
                    if task and task["Status"] in ["Not started", "In progress"]:
                        tasks.append(task)
                
                logger.info(f"✅ Fetched {len(tasks)} tasks.")
                return tasks

        except Exception as e:
            logger.error(f"❌ Notion Exception: {e}")
            return []

    def _map_task_properties(self, props):
        """Helper to map API properties to dictionary."""
        def get_val(key, type_key="rich_text"):
            if key not in props: return "N/A"
            obj = props[key]
            try:
                if type_key == "title":
                    return obj["title"][0]["plain_text"] if obj.get("title") else "Không tên"
                elif type_key == "date":
                    return obj["date"]["start"] if obj.get("date") else "Chưa đặt lịch"
                elif type_key in ["select", "status"]:
                    return obj[type_key]["name"] if obj.get(type_key) else "Trống"
                elif type_key == "relation":
                    return f"🔗 {len(obj.get('relation', []))} liên kết"
            except:
                return "Error"
            return ""

        return {
            "Task Name":    get_val("Name", "title"),
            "Deadline":     get_val("Hạn chót", "date"),
            "Status":       get_val("Trạng thái", "status"),
            "Type":         get_val("Loại nhiệm vụ", "select"),
            "Priority":     get_val("Độ ưu tiên", "select"),
        }

    def get_database_options(self):
        """Fetches status/priority options."""
        container_id = Config.NOTION_DATABASE_ID
        if not container_id: return {}
        
        try:
            with httpx.Client(timeout=30.0) as client:
                _, db_info = self._resolve_db_info(client, container_id)
                if not db_info: return {}

                props = db_info.get("properties", {})
                
                def get_opts(name, key="select"):
                    if name not in props: return []
                    raw = props[name].get(key, {}).get("options", [])
                    return [o["name"] for o in raw]

                return {
                    "Trạng thái": get_opts("Trạng thái", "status"),
                    "Loại nhiệm vụ": get_opts("Loại nhiệm vụ", "select"),
                    "Độ ưu tiên": get_opts("Độ ưu tiên", "select"),
                }
        except Exception as e:
            logger.error(f"❌ Metadata Error: {e}")
            return {}

    def get_review_notes(self):
        """Fetches notes with '🔴 Cần xem lại' status."""
        raw_db_id = Config.NOTION_DB_GHI_CHEP_ID
        if not raw_db_id: return []

        # Ensure ID format
        db_id = raw_db_id.replace("-", "")
        db_id = f"{db_id[:8]}-{db_id[8:12]}-{db_id[12:16]}-{db_id[16:20]}-{db_id[20:]}"

        payload = {
            "filter": {
                "property": "Độ hiểu bài",
                "select": { "equals": "🔴 Cần xem lại" }
            }
        }
        
        logger.info(f"🔄 Searching review notes in DB: {db_id}")
        
        try:
            with httpx.Client(timeout=30.0) as client:
                # 1. Resolve Data Source ID (New API 2025-09-03)
                real_source_id, _ = self._resolve_db_info(client, db_id)
                if not real_source_id: 
                    logger.error("❌ Could not resolve Data Source ID.")
                    return []

                # 2. Use Data Sources Query Endpoint
                query_url = f"https://api.notion.com/v1/data_sources/{real_source_id}/query"
                
                resp = client.post(query_url, headers=self.headers, json=payload)
                
                # Retry logic for property mismatch
                if resp.status_code == 400:
                     err_body = resp.json()
                     # Only switch filter if it's a validation error about property
                     if err_body.get("code") == "validation_error":
                        logger.warning("⚠️ Filter select failed, switching to status...")
                        # Backup: try 'Status' or 'Trạng thái' if 'Độ hiểu bài' fails
                        # For now, let's just try filtering by 'Trạng thái' if the user has that common column
                        if "status" in payload["filter"]:
                            pass # Already tried
                        else:
                            # Use new payload structure for status
                            payload = {
                                "filter": {
                                    "property": "Trạng thái",
                                    "status": { "equals": "In progress" } # Generic fallback, user might need to customize
                                }
                            }
                            resp = client.post(query_url, headers=self.headers, json=payload)
                
                if resp.status_code != 200:
                    logger.error(f"❌ Query Error: {resp.status_code} -Body: {resp.text}")
                    return []

                pages = resp.json().get("results", [])
                logger.info(f"✅ Found {len(pages)} notes.")
                return pages

        except Exception as e:
            logger.error(f"❌ Review Notes Error: {e}")
            return []

    def fetch_page_content(self, page_id):
        """Recursively fetches all content blocks of a page."""
        with httpx.Client(timeout=60.0) as client:
            return self._fetch_children_recursive(client, page_id)

    def _fetch_children_recursive(self, client, block_id, depth=0):
        url = f"https://api.notion.com/v1/blocks/{block_id}/children"
        all_content = []
        
        try:
            response = client.get(url, headers=self.headers)
            if response.status_code != 200: return []
            
            blocks = response.json().get("results", [])
            for block in blocks:
                text = self._process_block(block, depth)
                if text: all_content.append(text)
                
                if block.get("has_children", False):
                    children = self._fetch_children_recursive(client, block["id"], depth + 1)
                    all_content.extend(children)
        except:
            pass
        return all_content

    def _process_block(self, block, depth=0):
        """Formats a block into text."""
        b_type = block.get("type")
        indent = "  " * depth
        content = ""
        
        def ex_text(rich_list):
            return "".join([t.get("plain_text", "") for t in rich_list])

        if b_type == "paragraph":
            content = ex_text(block["paragraph"].get("rich_text", []))
        elif b_type in ["heading_1", "heading_2", "heading_3"]:
            level = int(b_type.split("_")[1])
            content = f"\n{'#'*level} {ex_text(block[b_type].get('rich_text', []))}"
        elif b_type == "bulleted_list_item":
            content = f"• {ex_text(block['bulleted_list_item'].get('rich_text', []))}"
        # ... (Include other types as needed from original) ...
        elif b_type == "callout":
            icon = block["callout"].get("icon", {}).get("emoji", "💡")
            content = f"> {icon} {ex_text(block['callout'].get('rich_text', []))}"
            
        return f"{indent}{content}" if content.strip() else ""
