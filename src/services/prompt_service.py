import httpx
from src.config.settings import Config
from src.utils.logger import logger
from src.services.notion import NotionService

class PromptService(NotionService):
    def __init__(self):
        super().__init__()
        
        # Override token if a specific one is provided for prompts
        token = Config.NOTION_PROMPT_TOKEN or Config.NOTION_TOKEN
        
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": Config.NOTION_VERSION,
            "Content-Type": "application/json"
        }
        
        # Format the ID immediately upon init
        raw_id = Config.NOTION_PROMPT_DATABASE_ID
        if raw_id:
             clean_id = raw_id.replace("-", "")
             if len(clean_id) == 32:
                 self.db_id = f"{clean_id[:8]}-{clean_id[8:12]}-{clean_id[12:16]}-{clean_id[16:20]}-{clean_id[20:]}"
             else:
                 self.db_id = raw_id 
        else:
             self.db_id = None
             
        self._cache = {}

    def get_prompt(self, project_name, prompt_name):
        """
        Fetches a prompt config from Notion by Project and Name.
        """
        if not self.db_id:
            logger.error("❌ NOTION_PROMPT_DATABASE_ID is missing")
            return None

        # Check cache
        cache_key = f"{project_name}:{prompt_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            with httpx.Client(timeout=30.0) as client:
                # Resolve the ID using NotionService logic (Data Source vs Database)
                real_source_id, _ = self._resolve_db_info(client, self.db_id)
                
                if not real_source_id:
                    logger.error(f"❌ Could not resolve Data Source ID for Prompt DB ({self.db_id})")
                    return None

                # Use the Data Sources endpoint as seen in NotionService
                # But fallback to databases endpoint if it's a standard DB?
                # NotionService uses /data_sources/{id}/query unconditionally after resolution return.
                # Let's verify _resolve_db_info implementation in notion.py
                # It returns the id from `data_sources` array if present, else container_id.
                # If it returns container_id, likely we should use /databases/{id}/query ??
                # In NotionService.get_tasks:
                # query_url = f"https://api.notion.com/v1/data_sources/{real_source_id}/query"
                # So let's stick to consistent usage.
                
                url = f"https://api.notion.com/v1/data_sources/{real_source_id}/query"
                
                # Payload for query
                payload = {
                    "filter": {
                        "and": [
                            {
                                "property": "Name",
                                "title": {
                                    "equals": prompt_name
                                }
                            },
                            {
                                "property": "Project",
                                "multi_select": {
                                    "contains": project_name
                                }
                            }
                        ]
                    }
                }

                resp = client.post(url, headers=self.headers, json=payload)
                
                # If 400/Invalid URL for data_sources, maybe try standard databases query as fallback?
                # But let's trust NotionService logic first.
                
                if resp.status_code != 200:
                    logger.error(f"❌ Error fetching prompt '{prompt_name}': {resp.status_code} -Body: {resp.text}")
                    return None

                results = resp.json().get("results", [])
                if not results:
                    logger.warning(f"⚠️ Prompt not found in Notion: {project_name} -> {prompt_name}")
                    return None

                # Parse the first match
                page = results[0]
                props = page.get("properties", {})
                
                def get_rich_text(key):
                    rt = props.get(key, {}).get("rich_text", [])
                    return "".join([t["plain_text"] for t in rt]) if rt else ""
                
                def get_select(key):
                    return props.get(key, {}).get("select", {}).get("name", "")

                prompt_data = {
                    "system_prompt": get_rich_text("System Prompt"),
                    "user_template": get_rich_text("User Template"),
                    "model": get_select("Model") or Config.GEMINI_MODEL_FLASH
                }

                # Save to cache
                self._cache[cache_key] = prompt_data
                logger.info(f"✅ Loaded prompt: {prompt_name} ({prompt_data['model']})")
                return prompt_data

        except Exception as e:
            logger.error(f"❌ Exception fetching prompt: {e}")
            return None
