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
        container_id = Config.NOTION_DB_TASK
        if not container_id:
            logger.error("❌ NOTION_DB_TASK missing")
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
        container_id = Config.NOTION_DB_TASK
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
            },
            "page_size": 50
        }

        logger.info(f"🔄 Searching review notes in DB: {db_id}")

        all_pages = []

        try:
            with httpx.Client(timeout=30.0) as client:
                # 1. Resolve Data Source ID (New API 2025-09-03)
                real_source_id, _ = self._resolve_db_info(client, db_id)
                if not real_source_id:
                    logger.error("❌ Could not resolve Data Source ID.")
                    return []

                # 2. Use Data Sources Query Endpoint with pagination
                query_url = f"https://api.notion.com/v1/data_sources/{real_source_id}/query"

                cursor = None
                max_fetch = 200

                while True:
                    current_payload = dict(payload)
                    if cursor:
                        current_payload["start_cursor"] = cursor

                    resp = client.post(query_url, headers=self.headers, json=current_payload)

                    # Retry logic for property mismatch
                    if resp.status_code == 400:
                        err_body = resp.json()
                        if err_body.get("code") == "validation_error":
                            logger.warning("⚠️ Filter select failed, switching to status...")
                            current_payload.update({
                                "filter": {
                                    "property": "Trạng thái",
                                    "status": { "equals": "In progress" }
                                }
                            })
                            resp = client.post(query_url, headers=self.headers, json=current_payload)

                    if resp.status_code != 200:
                        logger.error(f"❌ Query Error: {resp.status_code} -Body: {resp.text}")
                        return []

                    data = resp.json()
                    pages = data.get("results", [])
                    all_pages.extend(pages)
                    logger.info(f"📄 Fetched {len(pages)} pages (total so far: {len(all_pages)})")

                    if not data.get("has_more") or len(all_pages) >= max_fetch:
                        break
                    cursor = data.get("next_cursor")

                logger.info(f"✅ Found {len(all_pages)} notes total.")
                return all_pages

        except Exception as e:
            logger.error(f"❌ Review Notes Error: {e}")
            return []

    def fetch_page_content(self, page_id, progress_callback=None):
        """Recursively fetches all content blocks of a page in parallel using BFS to avoid deadlocks."""
        from concurrent.futures import ThreadPoolExecutor
        import time

        class BlockNode:
            def __init__(self, block_id, depth=0):
                self.block_id = block_id
                self.depth = depth
                self.text = ""
                self.child_nodes = []

        root_node = BlockNode(page_id, depth=-1)
        pending_nodes = [root_node]
        level = 1

        with httpx.Client(timeout=60.0) as client:
            with ThreadPoolExecutor(max_workers=10) as executor:
                while pending_nodes:
                    if progress_callback:
                        if level == 1:
                            progress_callback("fetching_notion", 10, "📖 Đang tải cấu trúc bài viết từ Notion...")
                        else:
                            progress_callback("fetching_notion", 15 if level == 2 else 30, f"📖 Đang tải song song {len(pending_nodes)} khối nội dung từ Notion...")

                    def fetch_node_children(node):
                        url = f"https://api.notion.com/v1/blocks/{node.block_id}/children"
                        try:
                            retries = 3
                            backoff = 0.5
                            response = None
                            for attempt in range(retries):
                                response = client.get(url, headers=self.headers)
                                if response.status_code == 429:
                                    retry_after = float(response.headers.get("Retry-After", backoff))
                                    time.sleep(retry_after)
                                    backoff *= 2
                                    continue
                                break
                            if response and response.status_code == 200:
                                return response.json().get("results", [])
                        except Exception as e:
                            logger.error(f"Error fetching children for block {node.block_id}: {e}")
                        return []

                    future_to_node = {
                        executor.submit(fetch_node_children, node): node
                        for node in pending_nodes
                    }

                    next_pending = []
                    for future in future_to_node:
                        node = future_to_node[future]
                        results = future.result()
                        for block in results:
                            text = self._process_block(block, node.depth + 1)
                            child = BlockNode(block["id"], depth=node.depth + 1)
                            child.text = text
                            node.child_nodes.append(child)
                            if block.get("has_children", False):
                                next_pending.append(child)

                    pending_nodes = next_pending
                    level += 1

        all_content = []
        def dfs(node):
            if node.text:
                all_content.append(node.text)
            for child in node.child_nodes:
                dfs(child)

        dfs(root_node)
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

    def retrieve_page(self, page_id):
        """Retrieves a page by ID."""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, headers=self.headers)
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"❌ Retrieve Page Error: {response.status_code} -Body: {response.text}")
                    return None
        except Exception as e:
            logger.error(f"❌ Retrieve Page Exception: {e}")
            return None

    def update_page_property(self, page_id, property_name, value, type_key="date"):
        """Updates a property of a page."""
        url = f"https://api.notion.com/v1/pages/{page_id}"
        
        # Construct the property object based on type
        prop_body = {}
        if type_key == "date":
             prop_body = { "date": { "start": value } }
        elif type_key == "select":
             prop_body = { "select": { "name": value } }
        # Add other types if needed
        
        payload = {
            "properties": {
                property_name: prop_body
            }
        }
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.patch(url, headers=self.headers, json=payload)
                if response.status_code == 200:
                    logger.info(f"✅ Updated {property_name} for page {page_id}")
                    return True
                else:
                    logger.error(f"❌ Update Error: {response.status_code} -Body: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"❌ Update Exception: {e}")
            return False
