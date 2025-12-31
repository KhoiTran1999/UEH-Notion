import os
import sys
from dotenv import load_dotenv

# Add the src directory to sys.path if running from root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.notion_client import get_tasks_from_notion, get_database_options
from src.ai_helper import analyze_tasks, generate_voice_script
from src.telegram_bot import send_telegram_message, send_telegram_voice
from src.voice_generator import generate_voice_summary

def main():
    # Load environment variables (from .env local or GitHub Secrets)
    load_dotenv()
    
    print("🚀 Bắt đầu Daily Report Job...")
    
    # 1. Fetch Tasks
    tasks = get_tasks_from_notion()
    
    # Fetch DB Options for AI Context
    db_options = get_database_options()
    
    if not tasks:
        print("⚠️ Không lấy được task hoặc danh sách rỗng (do filter).")
        
    print(f"✅ Đã lấy {len(tasks)} tasks.")

    # 2. Analyze with AI
    print("🧠 Đang phân tích với AI...")
    summary_message = analyze_tasks(tasks, db_options)
    print("📝 Nội dung tin nhắn:")
    print(summary_message)
    
    # 3. Send Text to Telegram
    print("📨 Đang gửi Telegram Text...")
    send_telegram_message(summary_message)
    
    # 4. Generate & Send Voice
    if tasks:
        print("🎙️ Đang xử lý Voice...")
        
        # a) Re-script for audio
        print("   ✍️ Đang viết lại kịch bản nói...")
        voice_script = generate_voice_script(summary_message)
        # print(f"   📜 Kịch bản Voice: {voice_script}") # Debug if needed
        
        # b) Generate Audio
        print("   🔊 Đang tạo file Audio (Edge-TTS)...")
        audio_file = generate_voice_summary(voice_script, "daily_report_voice.mp3")
        
        if audio_file:
            print(f"   📨 Đang gửi Voice Telegram...")
            send_telegram_voice(audio_file, caption="🎧 Bản tin Audio Morning Review")
        else:
            print("   ❌ Không tạo được file audio.")
    else:
        print("🔕 Không có task nên bỏ qua phần tạo Voice.")
    
    print("🏁 Hoàn thành!")

if __name__ == "__main__":
    main()
