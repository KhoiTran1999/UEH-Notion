import os
import sys
import httpx
from src.config.settings import Config

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def list_dbs():
    token = Config.NOTION_TOKEN
    version = Config.NOTION_VERSION
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": version,
        "Content-Type": "application/json"
    }
    
    print("🔍 Searching for databases...")
    
    url = "https://api.notion.com/v1/search"
    payload = {
        "filter": {
            "value": "database",
            "property": "object"
        }
    }
    
    with httpx.Client() as client:
        resp = client.post(url, headers=headers, json=payload)
        
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            print(f"✅ Found {len(results)} databases:")
            for db in results:
                try:
                    title = db.get("title", [])
                    plain_title = title[0]["plain_text"] if title else "Untitled"
                    print(f" - [{plain_title}] ID: {db['id'].replace('-', '')}")
                except:
                    print(f" - [Error parsing db] ID: {db['id']}")
        else:
            print(f"❌ Error: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    list_dbs()
