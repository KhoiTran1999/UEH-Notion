import os
import json
from datetime import datetime, timedelta, timezone
from google import genai

def analyze_tasks(tasks, db_options=None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ Thiếu GEMINI_API_KEY trong biến môi trường."
    
    if not tasks:
        # Fallback message even if no tasks
        return "Chào buổi sáng! 🌞 Hôm nay bạn không có task nào phải làm. Hãy tận hưởng ngày nghỉ hoặc học thêm kỹ năng mới nhé! 🚀"

    try:
        client = genai.Client(api_key=api_key)
        
        # Convert tasks to a formatted string
        tasks_str = json.dumps(tasks, ensure_ascii=False, indent=2)
        
        # Format Options string
        status_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Trạng thái", [])]) if db_options else ""
        type_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Loại nhiệm vụ", [])]) if db_options else ""
        priority_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Độ ưu tiên", [])]) if db_options else ""

        # Construct dynamic prompt section
        tags_instruction = ""
        if db_options:
            tags_instruction = f"""
   • Trạng thái: {status_opts}
   • Loại nhiệm vụ: {type_opts}
   • Độ ưu tiên: {priority_opts}
"""
        else:
             # Fallback to hardcoded if no options fetched
             tags_instruction = """
   • Trạng thái: "⚪ Not started", "🔵 In progress", "🟢 Done".
   • Loại nhiệm vụ: "🏠 Bài tập về nhà", "💡 Học lý thuyết", "🕵️ Tự nghiên cứu", "👨‍👩‍👧‍👦 Làm việc nhóm", "📢 Thuyết trình", "🎯 Thi kết thúc học phần", "📝 Kiểm tra giữa kỳ", "🚀 Dự án".
   • Độ ưu tiên: "🔥 Quan trọng & Khẩn cấp", "⏳ Quan trọng & Không khẩn cấp", "⚠️ Khẩn cấp & Không quan trọng", "💩 Không quan trọng & Không khẩn cấp".
"""

        prompt = f"""
Bạn là một Chuyên gia Quản trị năng suất (Productivity Coach).
Thời gian hiện tại: {datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")}
Dưới đây là danh sách nhiệm vụ từ Notion của tôi:
{tasks_str}

Nhiệm vụ của bạn là lập kế hoạch tác chiến dựa trên tư duy Ma trận Eisenhower và kỹ thuật "Eat the Frog". 

**📌 QUY TẮC NGÔN NGỮ & ĐỊNH DẠNG BẮT BUỘC**:
1. GIỮ NGUYÊN 100% các thuật ngữ và Emoji sau (Không được dịch, không được thay emoji):
{tags_instruction}
2. Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách.
3. Phản hồi bằng tiếng Việt thân thiện, hào hứng, tối ưu cho Telegram.
4. Không cần chào hỏi và giới thiệu gì hết mà vào thẳng nội dung.
5. Không giải thích lại các thuật ngữ như "Eat the Frog 🐸" mà chỉ tập trung vào liệt kê các nhiệm vụ.

**🎯 CẤU TRÚC BẢN TIN CHIẾN LƯỢC**:
1. **Tổng quan**: Tóm tắt số lượng task theo trạng thái (vd: 2 ⚪ Not started).
2. **Nhiệm vụ trọng tâm (Eat the Frog 🐸)**: Chọn ra 1 nhiệm vụ quan trọng/gần hạn nhất để làm ngay.
3. **Phân loại chiến thuật**: Liệt kê các task còn lại theo nhóm Độ ưu tiên (🔥, ⏳, ⚠️, 💩).
4. **Lời khuyên hành động**: Đưa ra lời khuyên ngắn gọn để Khôi hoàn thành task tốt hơn.

**📖 VÍ DỤ OUTPUT MẪU**:
• Hiện tại bạn đang có *3* nhiệm vụ: *2 ⚪ Not started*, 1 *🔵 In progress*.

**🔥 NHIỆM VỤ TRỌNG TÂM (EAT THE FROG)**
[Ưu tiên xử lý công việc "Hạn chót".]

**💪 PHÂN LOẠI CHIẾN THUẬT**
[Phân loại các nhiệm vụ theo "Độ ưu tiên".]

**💡 LỜI KHUYÊN**:
[Hãy đưa ra lời khuyên ngắn gọn để hoàn thành task tốt hơn]

---
**BÂY GIỜ, HÃY DỰA VÀO DỮ LIỆU THỰC TẾ {tasks_str} ĐỂ VIẾT BẢN TIN CHO HÔM NAY:**
"""
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # Or gemini-1.5-flash
            contents=prompt
        )
        
        return response.text
    except Exception as e:
        return f"❌ Lỗi khi gọi AI: {str(e)}"

def generate_voice_script(original_text):
    """
    Sử dụng AI để viết lại nội dung thành kịch bản nói tự nhiên.
    Loại bỏ emoji, markdown, chuyển các ký tự đặc biệt thành lời nói.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return original_text # Fallback

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
Bạn là biên tập viên trong vai trò trợ lý của tôi. 
Thời gian hiện tại: {datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")}
Dưới đây là nội dung bản tin văn bản:
---
{original_text}
---

Nhiệm vụ của bạn:
1. Viết lại nội dung trên thành **KỊCH BẢN ĐỌC (Voice Script)** ngắn gọn và đơn giản là liệt kê lại các nhiệm vụ để phát thanh viên đọc lại.
2. **Yêu cầu tuyệt đối**:
   - Loại bỏ toàn bộ Emoji, ký tự đặc biệt (*, -, •, ...).
   - Chuyển đổi các từ viết tắt (vd: "deadline") thành văn nói tự nhiên nếu cần (hoặc giữ nguyên nếu thông dụng).
   - Thêm các từ nối để câu văn mượt mà, cảm xúc (vd: "Thưa bạn", "Tiếp theo là", "Đặc biệt lưu ý").
   - Giọng điệu: Hào hứng, năng động, ấm áp, như một người bạn đồng hành.
   - Mở đầu bằng lời chào hỏi ngắn gọn.
   - Chỉ tập trung vào nhiệm vụ và không giải thích thêm thông tin không liên quan.
   - **Chỉ trả về nội dung text thuần túy để đưa vào máy đọc.** Không bao gồm chú thích (vd: [nhạc nền], [vui vẻ]...).

Hãy viết lại ngay bây giờ:
"""
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        return response.text.strip()

    except Exception as e:
        print(f"❌ Lỗi Re-Scripting: {e}")
        return original_text

def generate_quiz(content):
    """
    Tạo bộ câu hỏi ôn tập từ nội dung ghi chép.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "❌ Thiếu GEMINI_API_KEY."

    if not content:
        return "⚠️ Nội dung bài học trống, không thể tạo câu hỏi."

    try:
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
Bạn là một Chuyên gia Giáo dục và Trợ lý Học tập Thông minh.
Nhiệm vụ: Phân tích ghi chép và tạo bộ câu hỏi ôn tập Active Recall tối ưu cho từng loại môn học.

--- NỘI DUNG GHI CHÉP ---
{content}
-------------------------

**XÁC ĐỊNH CHIẾN THUẬT ĐẶT CÂU HỎI**
Dựa trên nội dung ghi chép, hãy xác định môn học thuộc nhóm nào sau đây để áp dụng cách đặt câu hỏi tương ứng:
- Nhóm Ngôn ngữ (Tiếng Anh): Tập trung vào vựng (vocab), ngữ pháp, collocations, idioms,...
- Nhóm Tính toán/Logic (Toán, Kinh tế): Tập trung vào công thức, cách giải bài toán tối ưu, ý nghĩa của các biến số và đồ thị (Cung - Cầu, Ma trận, Tích phân),...
- Nhóm Lý thuyết/Hệ thống (Triết học, Luật, Tâm lý): Tập trung vào khái niệm, tư duy hệ thống, các quy định pháp lý hoặc hành vi con người,...

**TẠO BỘ CÂU HỎI (3-5 CÂU)**
YÊU CẦU ĐỊNH DẠNG (HTML Telegram Mode):
1. Mỗi câu hỏi phải in đậm bằng thẻ <b> và bắt đầu bằng "🎯 <b>Q[số]: ..."
2. Mỗi câu trả lời phải nằm trọn vẹn trong thẻ <tg-spoiler>.
3. Sau mỗi cặp Q&A phải có một dòng trống để tránh dính Spoiler trên di động.
4. Ngôn ngữ: Tiếng Việt (Trừ các thuật ngữ chuyên ngành tiếng Anh).

OUTPUT:
🎯 <b>Q1: Nội dung câu hỏi...?</b>
👉 <tg-spoiler>Đáp án ngắn gọn...</tg-spoiler>

🎯 <b>Q2: Nội dung câu hỏi...?</b>
👉 <tg-spoiler>Đáp án ngắn gọn...</tg-spoiler>

---
Hãy bắt đầu tạo ngay bộ câu hỏi cho ghi chép trên:
"""
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # Upscale model for better reasoning if available, else 1.5-flash
            contents=prompt
        )
        return response.text.strip()

    except Exception as e:
        return f"❌ Lỗi tạo câu hỏi: {str(e)}"
