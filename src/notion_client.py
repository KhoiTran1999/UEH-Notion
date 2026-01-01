import os
import httpx
from dotenv import load_dotenv

load_dotenv()

def get_tasks_from_notion():
    token = os.getenv("NOTION_TOKEN")
    container_id = os.getenv("NOTION_DATABASE_ID")

    if not token or not container_id:
        print("❌ Thiếu Notion Token hoặc ID trong environment variables")
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2025-09-03", 
        "Content-Type": "application/json"
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            # --- BƯỚC 1: LẤY ID CỦA NGUỒN DỮ LIỆU THỰC TẾ (Source Container Logic) ---
            real_source_id, _ = _resolve_db_info(client, headers, container_id)
            if not real_source_id:
                return []

            # --- BƯỚC 2: QUERY DỮ LIỆU ---
            query_url = f"https://api.notion.com/v1/data_sources/{real_source_id}/query"
            
            # ⚠️ QUAN TRỌNG: Đã xóa phần "sorts" để tránh lỗi "Could not find property" như trong mẫu
            payload = {
                "page_size": 100
            }

            print(f"🔄 Đang tải tasks từ source...")
            response = client.post(query_url, headers=headers, json=payload)

            if response.status_code != 200:
                print(f"❌ Lỗi Query: {response.status_code}")
                print(response.text)
                return []

            data = response.json()
            results = data.get("results", [])
            tasks = []

            for page in results:
                props = page.get("properties", {})
                
                # Hàm helper lấy dữ liệu an toàn (Logic từ test_notion.py)
                def get_val(key, type_key="rich_text"):
                    if key not in props: return "N/A"
                    obj = props[key]
                    try:
                        # 1. Text/Title
                        if type_key == "title":
                            return obj["title"][0]["plain_text"] if obj.get("title") else "Không tên"
                        
                        # 2. Date
                        elif type_key == "date":
                            return obj["date"]["start"] if obj.get("date") else "Chưa đặt lịch"
                        
                        # 3. Select/Status
                        elif type_key in ["select", "status"]:
                            return obj[type_key]["name"] if obj.get(type_key) else "Trống"
                        
                        # 4. Relation (Liên kết database khác)
                        elif type_key == "relation":
                            relations = obj.get("relation", [])
                            return f"🔗 {len(relations)} liên kết" if relations else "Không có"
                            
                    except:
                        return "Error"
                    return ""

                # --- MAPPING CỘT (Theo tên chính xác trong test_notion.py) ---
                task = {
                    "Task Name":    get_val("Name", "title"),
                    "Deadline":     get_val("Hạn chốt", "date"),
                    "Status":       get_val("Trạng thái", "status"),
                    "Type":         get_val("Loại nhiệm vụ", "select"),
                    "Priority":     get_val("Độ ưu tiên", "select"),
                    
                    # Các cột Relation mới
                    "Hoc Phan":     get_val("DB Học Phần - UEH", "relation"),
                    "Chuong":       get_val("DB Chương", "relation"),
                    "Ghi Chep":     get_val("DB Ghi Chép", "relation")
                }
                if task["Status"] in ["Not started", "In progress"]:
                    tasks.append(task)
            
            print(f"✅ Đã lấy thành công {len(tasks)} tasks.")
            return tasks

    except Exception as e:
        print(f"❌ Exception querying Notion: {e}")
        return []

def _resolve_db_info(client, headers, container_id):
    """Helper để lấy Real Query ID và Info từ Container ID"""
    print(f"🔍 Đang kiểm tra Container: {container_id}...")
    container_url = f"https://api.notion.com/v1/databases/{container_id}"
    
    resp_container = client.get(container_url, headers=headers)
    
    if resp_container.status_code != 200:
        print(f"❌ Lỗi Container: {resp_container.status_code} - {resp_container.text}")
        return None, {}
    
    db_info = resp_container.json()
    data_sources = db_info.get("data_sources", [])
    
    if not data_sources:
        # Fallback: Container IS the DB
        return container_id, db_info
        
    real_source_id = data_sources[0]["id"]
    print(f"✅ Tìm thấy Data Source ID: {real_source_id}")
    return real_source_id, db_info

def get_database_options():
    """Lấy danh sách các options (Tags) của Trạng thái, Loại nhiệm vụ, Độ ưu tiên"""
    token = os.getenv("NOTION_TOKEN")
    container_id = os.getenv("NOTION_DATABASE_ID")
    
    if not token or not container_id:
        return {}

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2025-09-03", 
        "Content-Type": "application/json"
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            # Lấy db_info từ call đầu tiên, không call lại endpoint databases/{id} với source_id gây lỗi 404
            _, db_info = _resolve_db_info(client, headers, container_id)
            
            if not db_info:
                return {}

            props = db_info.get("properties", {})
            
            # Helper to extract names
            def get_options(prop_name, type_key="select"):
                if prop_name not in props: return []
                p = props[prop_name]
                options = []
                
                if type_key == "status":
                    raw_opts = p.get("status", {}).get("options", [])
                    options = [o["name"] for o in raw_opts]
                    
                elif type_key == "select":
                    raw_opts = p.get("select", {}).get("options", [])
                    options = [o["name"] for o in raw_opts]
                    
                return options

            return {
                "Trạng thái": get_options("Trạng thái", "status"),
                "Loại nhiệm vụ": get_options("Loại nhiệm vụ", "select"),
                "Độ ưu tiên": get_options("Độ ưu tiên", "select"),
            }

    except Exception as e:
        print(f"❌ Exception fetching metadata: {e}")
        return {}

# --- New Functions for Study Assistant ---

def extract_plain_text(rich_text_list):
    if not rich_text_list: return ""
    return "".join([t.get("plain_text", "") for t in rich_text_list])

def process_block(block, depth=0):
    """
    Xử lý hiển thị text của 1 block dựa trên type.
    Trả về chuỗi text đã định dạng.
    """
    b_type = block.get("type")
    indent = "  " * depth # Thụt đầu dòng để thể hiện cấp độ con
    text_content = ""
    
    # Lấy nội dung rich_text tùy theo loại block
    if b_type == "paragraph":
        text_content = extract_plain_text(block["paragraph"].get("rich_text", []))
    elif b_type in ["heading_1", "heading_2", "heading_3"]:
        level = int(b_type.split("_")[1])
        prefix = "#" * level
        raw = extract_plain_text(block[b_type].get("rich_text", []))
        text_content = f"\n{prefix} {raw}"
    elif b_type == "bulleted_list_item":
        raw = extract_plain_text(block["bulleted_list_item"].get("rich_text", []))
        text_content = f"• {raw}"
    elif b_type == "numbered_list_item":
        raw = extract_plain_text(block["numbered_list_item"].get("rich_text", []))
        text_content = f"1. {raw}"
    elif b_type == "to_do":
        checked = "x" if block["to_do"].get("checked") else " "
        raw = extract_plain_text(block["to_do"].get("rich_text", []))
        text_content = f"- [{checked}] {raw}"
    elif b_type == "callout":
        icon = block["callout"].get("icon", {}).get("emoji", "💡")
        raw = extract_plain_text(block["callout"].get("rich_text", []))
        text_content = f"> {icon} {raw}"
    elif b_type == "quote":
        raw = extract_plain_text(block["quote"].get("rich_text", []))
        text_content = f"> {raw}"
    
    # Các loại block chứa cấu trúc (không có text trực tiếp)
    elif b_type == "column_list":
        text_content = "" # Chỉ là container
    elif b_type == "column":
        text_content = f"\n--- [Cột] ---" 
    elif b_type == "code":
         raw = extract_plain_text(block["code"].get("rich_text", []))
         lang = block["code"].get("language", "text")
         text_content = f"\n```{lang}\n{raw}\n```"

    return f"{indent}{text_content}" if text_content.strip() else ""

def fetch_children_recursive(client, block_id, depth=0):
    """
    Hàm đệ quy: Lấy block con, in ra, và nếu block con đó có con nữa thì gọi lại chính nó.
    """
    token = os.getenv("NOTION_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28", # Use older version for stability with blocks if needed, or 2025-09-03
        "Content-Type": "application/json"
    }

    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    all_content = []
    
    try:
        response = client.get(url, headers=headers)
        if response.status_code != 200:
            return [f"Error fetching children: {response.status_code}"]
        
        blocks = response.json().get("results", [])
        
        for block in blocks:
            # 1. Lấy nội dung của chính block này
            text = process_block(block, depth)
            if text:
                all_content.append(text)
            
            # 2. KIỂM TRA ĐỆ QUY: Nếu block này có con (has_children = True), chui vào lấy tiếp
            if block.get("has_children", False):
                children_content = fetch_children_recursive(client, block["id"], depth + 1)
                all_content.extend(children_content)
                
    except Exception as e:
        all_content.append(f"Error recursive: {str(e)}")
        
    return all_content

def format_uuid(id_str):
    if not id_str: return ""
    id_str = id_str.replace("-", "").strip()
    return f"{id_str[:8]}-{id_str[8:12]}-{id_str[12:16]}-{id_str[16:20]}-{id_str[20:]}"

def get_review_notes():
    """
    Lấy danh sách các bài có trạng thái '🔴 Cần xem lại'
    """
    token = os.getenv("NOTION_TOKEN")
    raw_db_id = os.getenv("NOTION_DB_GHI_CHEP_ID", "2d96633f4324813b9d9eca9f85d2ea48")
    
    if not token: 
        print("❌ Thiếu Notion Token")
        return []

    db_id = format_uuid(raw_db_id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    payload = {
        "filter": {
            "property": "Độ hiểu bài",
            "select": { "equals": "🔴 Cần xem lại" }
        }
    }

    print(f"🔄 Đang tìm bài cần ôn tập từ DB {db_id}...")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json=payload)
            
            # Fallback logic nếu filter lỗi (ví dụ dùng status thay vì select)
            if resp.status_code == 400:
                 print("⚠️ Filter select lỗi, thử switch sang status...")
                 payload["filter"]["status"] = payload["filter"].pop("select")
                 resp = client.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json=payload)
            
            if resp.status_code != 200:
                print(f"❌ Lỗi Query Review Notes: {resp.status_code} - {resp.text}")
                return []

            pages = resp.json().get("results", [])
            print(f"✅ Tìm thấy {len(pages)} bài cần ôn tập.")
            return pages
            
    except Exception as e:
        print(f"❌ Exception querying review notes: {e}")
        return []

if __name__ == "__main__":
    # Test nhanh khi chạy trực tiếp file này
    t_list = get_tasks_from_notion()
    print("\n--- KẾT QUẢ ---")
    for t in t_list:
        print(f"📌 {t['Task Name']}")
        print(f"   🕒 {t['Deadline']} | 🚦 {t['Status']}")
        print("-" * 30)
