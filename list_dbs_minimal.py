import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def list_dbs():
    token = os.getenv("NOTION_TOKEN")
    version = os.getenv("NOTION_VERSION", "2025-09-03")
    
    if not token:
        print("❌ NO TOKEN FOUND")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": version,
        "Content-Type": "application/json"
    }
    
    print("🔍 Searching for databases (Minimal)...")
    
    url = "https://api.notion.com/v1/search"
    payload = {
        "filter": {
            "value": "database",
            "property": "object"
        }
    }
    
    try:
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
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    list_dbs()
