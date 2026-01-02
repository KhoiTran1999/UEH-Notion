import json
from datetime import datetime, timedelta, timezone
from google import genai
from src.config.settings import Config
from src.utils.logger import logger

class AIService:
    def __init__(self):
        if Config.GEMINI_API_KEY:
            self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        else:
            logger.error("❌ GEMINI_API_KEY is missing!")
            self.client = None

    def _get_vn_time(self):
        return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")

    def generate_content(self, prompt, model=Config.GEMINI_MODEL_FLASH):
        if not self.client: return "AI Service Unavailable"
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"❌ AI Generation Error: {e}")
            return f"Error: {str(e)}"

    def analyze_tasks(self, tasks, db_options=None):
        """Generates the daily report analysis."""
        if not tasks:
            return "Chào buổi sáng! 🌞 Hôm nay bạn không có task nào phải làm. Hãy tận hưởng ngày nghỉ nhé! 🚀"

        # Format Options string
        status_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Trạng thái", [])]) if db_options else ""
        type_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Loại nhiệm vụ", [])]) if db_options else ""
        priority_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Độ ưu tiên", [])]) if db_options else ""
        
        tags_instruction = f"""
   • Trạng thái: {status_opts}
   • Loại nhiệm vụ: {type_opts}
   • Độ ưu tiên: {priority_opts}
""" if db_options else ""

        tasks_str = json.dumps(tasks, ensure_ascii=False, indent=2)
        
        prompt = f"""
Bạn là một Chuyên gia Quản trị năng suất (Productivity Coach).
Thời gian hiện tại: {self._get_vn_time()}
Dưới đây là danh sách nhiệm vụ từ Notion của tôi:
{tasks_str}

Nhiệm vụ của bạn là lập kế hoạch tác chiến dựa trên tư duy Ma trận Eisenhower và kỹ thuật "Eat the Frog". 

**📌 QUY TẮC NGÔN NGỮ & ĐỊNH DẠNG BẮT BUỘC**:
1. GIỮ NGUYÊN 100% các thuật ngữ và Emoji sau:
{tags_instruction}
2. Chỉ dùng dấu * để bold text cho text và *** để bold text cho title, dùng dấu • cho danh sách.
3. Phản hồi bằng tiếng Việt thân thiện, hào hứng, tối ưu cho Telegram markdown.
4. Không cần chào hỏi và giới thiệu gì hết mà vào thẳng nội dung.
5. Không giải thích và nhắc đến các thuật ngữ như "Eat the Frog 🐸" hoặc "Ma trận Eisenhower" mà chỉ tập trung vào liệt kê các nhiệm vụ.

**🎯 CẤU TRÚC BẢN TIN CHIẾN LƯỢC**:
1. **Tổng quan**: Tóm tắt số lượng task theo trạng thái (vd: 2 ⚪ Not started).
2. **Nhiệm vụ trọng tâm (Eat the Frog 🐸)**: Chọn ra 1 nhiệm vụ quan trọng/gần "Hạn chót" (Deadline) nhất để làm ngay. Hãy ghi rõ hạn chót nếu có.
3. **Phân loại chiến thuật**: Liệt kê các task còn lại theo nhóm Độ ưu tiên (🔥, ⏳, ⚠️, 💩).
4. **Lời khuyên hành động**: Đưa ra lời khuyên ngắn gọn để Khôi hoàn thành task tốt hơn.
LƯU Ý: tên nhiệm vụ luôn phải được in đậm bằng dấu *

**📖 VÍ DỤ OUTPUT MẪU**:
• Hiện tại bạn đang có *3* nhiệm vụ: *2 ⚪ Not started*, 1 *🔵 In progress*.

***🔥 NHIỆM VỤ TRỌNG TÂM***
[Ưu tiên xử lý công việc "Tên task" (Hạn chót: dd/mm/yyyy).]

***💪 PHÂN LOẠI CHIẾN THUẬT***
[Phân loại các nhiệm vụ theo "Độ ưu tiên". Không nhắc lại công việc đã có trong phần "Nhiệm vụ trọng tâm".]

***💡 LỜI KHUYÊN***:
[Hãy đưa ra lời khuyên ngắn gọn để hoàn thành task tốt hơn]

---
**BÂY GIỜ, HÃY DỰA VÀO DỮ LIỆU THỰC TẾ ĐỂ VIẾT BẢN TIN CHO HÔM NAY:**
"""
        return self.generate_content(prompt, model=Config.GEMINI_MODEL_FLASH)

    def generate_voice_script(self, original_text):
        """Rewrites text for voice generation."""
        prompt = f"""
Bạn là người bạn thân và cũng là trợ lý trong công việc của Khôi.
Thời gian: {self._get_vn_time()}
Nội dung bản tin:
---
{original_text}
---

Nhiệm vụ: Viết lại thành **KỊCH BẢN ĐỌC (Voice Script)** ngắn gọn, tự nhiên, bỏ emoji, bỏ markdown. Giọng điệu: Hào hứng, năng động, ấm áp, như một người bạn đồng hành.
"""
        return self.generate_content(prompt, model=Config.GEMINI_MODEL_FLASH)

    def generate_quiz(self, content):
        """Generates quiz questions from review notes."""
        if not content: return "Nội dung trống."

        prompt = f"""
Bạn là một Chuyên gia Giáo dục và Trợ lý Học tập Thông minh.
Nhiệm vụ: Phân tích ghi chép và tạo bộ câu hỏi ôn tập Active Recall tối ưu cho từng loại môn học.

--- NỘI DUNG GHI CHÉP ---
{content}
-------------------------

[XÁC ĐỊNH CHIẾN THUẬT ĐẶT CÂU HỎI]
Dựa trên nội dung ghi chép, hãy xác định môn học thuộc nhóm nào sau đây để áp dụng cách đặt câu hỏi tương ứng:
- Nhóm Ngôn ngữ (Tiếng Anh): Sử dụng định dạng Trắc nghiệm điền vào chỗ trống (Fill-in-the-blank MCQ). Câu hỏi phải tạo ra một ngữ cảnh (context) cụ thể để người học hiểu cách dùng từ. 
- Nhóm còn lại Sử dụng câu hỏi vấn đáp trực tiếp (Q&A).

[TẠO 5 CÂU HỎI]
YÊU CẦU ĐỊNH DẠNG (HTML Telegram Mode):
1. Mỗi câu hỏi phải in đậm bằng thẻ <b> và bắt đầu bằng "🎯 <b>Q[số]: ..."
2. Nếu là câu hỏi trắc nghiệm: Liệt kê 4 đáp án A, B, C, D ở các dòng tiếp theo.
3. Mỗi câu trả lời phải nằm trọn vẹn trong thẻ <tg-spoiler>.
4. Sau mỗi cặp Q&A phải có một dòng trống để tránh dính Spoiler trên di động.
5. Ngôn ngữ: Tiếng Việt (Trừ các thuật ngữ chuyên ngành tiếng Anh, thì câu hỏi sẽ bằng tiếng Anh).

[OUTPUT Cho nhóm Ngôn ngữ tiếng Anh]
🎯 <b>Q1: [Câu hỏi hoặc Câu điền vào chỗ trống]</b>
[A. Option 1]
[B. Option 2]
[C. Option 3]
[D. Option 4]
👉 <tg-spoiler>Đáp án: ... (Giải thích: ...)</tg-spoiler>
Ví dụ:
🎯 <b>Q1: An …………… manager understands the personal needs of team members and creates a workplace where individuals feel heard.</b>
A. energetic
B. anxious
C. empathetic
D. ambitious
👉 <tg-spoiler>Đáp án: C. empathetic (Giải thích: Người quản lý thấu hiểu nhu cầu cá nhân là người có sự đồng cảm).</tg-spoiler>

[OUTPUT cho các nhóm còn lại:]
🎯 <b>Q1: Nội dung câu hỏi...?</b>
👉 <tg-spoiler>Đáp án ngắn gọn...</tg-spoiler>

🎯 <b>Q2: Nội dung câu hỏi...?</b>
👉 <tg-spoiler>Đáp án ngắn gọn...</tg-spoiler>

---
LƯU Ý: Không chào hỏi và giới thiệu gì hết mà vào thẳng nội dung trong OUTPUT.
Hãy bắt đầu tạo ngay bộ câu hỏi cho ghi chép trên:
"""
        return self.generate_content(prompt, model=Config.GEMINI_MODEL_FLASH)
