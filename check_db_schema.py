import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def inspect_db():
    token = os.getenv("NOTION_TOKEN")
    # Using the ID from notion_client.py default as fallback if env not set, 
    # but strictly we should use the one in env.
    raw_db_id = os.getenv("NOTION_DB_GHI_CHEP_ID", "2d96633f4324813b9d9eca9f85d2ea48")
    
    if not token:
        print("❌ Missing Token")
        return

    # Format UUID
    db_id = raw_db_id.replace("-", "")
    db_id = f"{db_id[:8]}-{db_id[8:12]}-{db_id[12:16]}-{db_id[16:20]}-{db_id[20:]}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    print(f"Checking DB: {db_id}")
    url = f"https://api.notion.com/v1/databases/{db_id}"
    
    with httpx.Client() as client:
        resp = client.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            props = data.get("properties", {})
            target = props.get("Độ hiểu bài")
            print(f"✅ Property 'Độ hiểu bài': {target}")
            if target:
                print(f"👉 Type: {target.get('type')}")
                opts = target.get(target.get('type'), {}).get('options', [])
                print(f"👉 Options: {[o['name'] for o in opts]}")
        else:
            print(f"❌ Error: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    inspect_db()
