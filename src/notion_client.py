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

if __name__ == "__main__":
    # Test nhanh khi chạy trực tiếp file này
    t_list = get_tasks_from_notion()
    print("\n--- KẾT QUẢ ---")
    for t in t_list:
        print(f"📌 {t['Task Name']}")
        print(f"   🕒 {t['Deadline']} | 🚦 {t['Status']}")
        print("-" * 30)
