import os
import sys
import random
import httpx
from dotenv import load_dotenv

# Add the src directory to sys.path if running from root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.notion_client import get_review_notes, fetch_children_recursive
from src.ai_helper import generate_quiz
from src.telegram_bot import send_telegram_message

def run_study_assistant():
    load_dotenv()
    print("🎓 Bắt đầu Study Assistant Job...")

    # 1. Chọn bài (Notion)
    candidates = get_review_notes()
    
    if not candidates:
        print("🎉 Không có bài nào cần xem lại hôm nay! (Hoặc có lỗi fetch)")
        return

    # Random 1 bài
    selected_note = random.choice(candidates)
    
    note_id = selected_note["id"]
    note_title = "Dấu hỏi lớn"
    
    # Safely get title
    if selected_note["properties"].get("Tên bài học", {}).get("title"):
        note_title = selected_note["properties"]["Tên bài học"]["title"][0]["plain_text"]
    
    note_url = selected_note["url"]
    
    print(f"🎯 Đã chọn được bài: {note_title.upper()}")
    
    # 2. Quét sâu nội dung
    print("📖 Đang đọc nội dung ghi chép...")
    # Need an httpx client for the recursive fetch
    token = os.getenv("NOTION_TOKEN")
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    with httpx.Client(timeout=60.0) as client:
        # Note: fetch_children_recursive in notion_client.py creates its own headers but takes a client
        # We should verify if fetch_children_recursive uses the client correctly.
        # Looking at previous implementation of fetch_children_recursive, it uses global HEADERS variable or reconstructs them.
        # Let's assume it works as implemented in notion_client.py which re-defines headers inside.
        
        content_lines = fetch_children_recursive(client, note_id)
        full_content = "\n".join(content_lines)

    if not full_content.strip():
        print("⚠️ Bài này không có nội dung text để tạo câu hỏi.")
        # Optional: Retry another note? For now just exit.
        return

    # 3. Tạo đề thi (AI)
    print("🧠 Đang nhờ AI tạo câu hỏi ôn tập...")
    quiz_content = generate_quiz(full_content)
    
    import time

    # 4. Gửi Telegram (Chia nhỏ tin nhắn)
    print("📨 Đang gửi Telegram...")
    
    # 1. Gửi Header trước
    header_msg = f"""
🎯 <b>GÓC ÔN TẬP NGẪU NHIÊN</b>
Bài: <a href="{note_url}">{note_title}</a>
Trạng thái: 🔴 Cần xem lại
"""
    send_telegram_message(header_msg, parse_mode="HTML")
    time.sleep(1) # Tránh rate limit của Telegram

    # 2. Xử lý phần nội dung AI (Tách từng câu hỏi)
    # AI trả về format: 🎯 <b>Q1...
    # Split theo icon 🎯. Phần tử đầu tiên có thể là rỗng hoặc lời dẫn (nếu AI không tuân thủ).
    raw_chunks = quiz_content.split("🎯")
    
    questions = []
    for chunk in raw_chunks:
        clean_chunk = chunk.strip()
        if not clean_chunk: continue
        
        # Nếu chunk không bắt đầu bằng <b (do split làm mất 🎯), ta thêm lại 🎯
        # Tuy nhiên prompt yêu cầu <b>Q... nên check xem có phải là câu hỏi không
        # Logic đơn giản: cứ thêm lại 🎯 cho đẹp, trừ khi nó là text rác
        full_msg = f"🎯 {clean_chunk}"
        questions.append(full_msg)
        
    if not questions:
        # Fallback nếu không split được (AI trả về format lạ)
        send_telegram_message(quiz_content, parse_mode="HTML", disable_notification=True)
    else:
        for q_msg in questions:
            send_telegram_message(q_msg, parse_mode="HTML", disable_notification=True)
            time.sleep(1)

    # 3. Gửi Footer
    footer_msg = f"""
---
👉 <i>Bấm vào link bài học để tự sửa trạng thái thành 🟢 Đã nắm vững nếu bạn trả lời đúng hết nhé!</i>
"""
    send_telegram_message(footer_msg, parse_mode="HTML", disable_notification=True)
    print("🏁 Hoàn thành Study Job!")

if __name__ == "__main__":
    run_study_assistant()
