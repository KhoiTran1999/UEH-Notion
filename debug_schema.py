import os
import sys
import httpx
from src.config.settings import Config

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

def debug_db():
    token = Config.NOTION_TOKEN
    db_id = Config.NOTION_DB_GHI_CHEP_ID
    version = Config.NOTION_VERSION
    
    print(f"Token: {token[:4]}...{token[-4:]}")
    print(f"DB ID: {db_id}")
    print(f"Version: {version}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": version,
        "Content-Type": "application/json"
    }
    
    # Format UUID if needed
    if "-" not in db_id:
         db_id = f"{db_id[:8]}-{db_id[8:12]}-{db_id[12:16]}-{db_id[16:20]}-{db_id[20:]}"

    url = f"https://api.notion.com/v1/databases/{db_id}"
    
    print(f"Fetching DB info from: {url}")
    with httpx.Client() as client:
        resp = client.get(url, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            props = data.get("properties", {})
            print("\n✅ Database Properties:")
            for name, prop in props.items():
                p_type = prop["type"]
                print(f" - [{name}] ({p_type})")
                if p_type in ["select", "status"]:
                    options = prop.get(p_type, {}).get("options", [])
                    print(f"   Options: {[o['name'] for o in options]}")
        else:
            print(f"❌ Error: {resp.status_code}")
            print(resp.text)

if __name__ == "__main__":
    debug_db()
