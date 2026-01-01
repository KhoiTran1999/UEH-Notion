import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def check_id():
    token = os.getenv("NOTION_TOKEN")
    version = os.getenv("NOTION_VERSION", "2025-09-03")
    
    # ID from settings (hardcoded from logs)
    raw_id = os.getenv("NOTION_DB_GHI_CHEP_ID", "2d96633f4324813b9d9eca9f85d2ea48")
    
    # Format
    if "-" not in raw_id:
         f_id = f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"
    else:
         f_id = raw_id
         
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": version,
        "Content-Type": "application/json"
    }

    print(f"🕵️ Checking ID: {f_id}")

    with httpx.Client() as client:
        # 1. Check as Database
        print("1️⃣ Checking as DATABASE...")
        url_db = f"https://api.notion.com/v1/databases/{f_id}"
        resp_db = client.get(url_db, headers=headers)
        print(f"   Status: {resp_db.status_code}")
        if resp_db.status_code == 200:
            print("   ✅ IT IS A DATABASE!")
            print(f"   Name: {resp_db.json().get('title', [{}])[0].get('plain_text', 'Untitled')}")
        else:
            print(f"   ❌ Not a DB (Body: {resp_db.text})")

        # 2. Check as Page
        print("\n2️⃣ Checking as PAGE...")
        url_page = f"https://api.notion.com/v1/pages/{f_id}"
        resp_page = client.get(url_page, headers=headers)
        print(f"   Status: {resp_page.status_code}")
        if resp_page.status_code == 200:
            print("   ✅ IT IS A PAGE!")
            print("   (You probably copied the Page Link instead of Database Link)")
        else:
            print(f"   ❌ Not a Page either.")

if __name__ == "__main__":
    check_id()
