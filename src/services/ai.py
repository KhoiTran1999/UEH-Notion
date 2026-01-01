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
3. Phản hồi bằng tiếng Việt thân thiện, hào hứng, tối ưu cho Telegram HTML.
4. Không cần chào hỏi và giới thiệu gì hết mà vào thẳng nội dung.

**🎯 CẤU TRÚC BẢN TIN CHIẾN LƯỢC**:
1. **Tổng quan**: Tóm tắt số lượng task.
2. **Nhiệm vụ trọng tâm (Eat the Frog 🐸)**: Chọn ra 1 nhiệm vụ quan trọng nhất.
3. **Phân loại chiến thuật**: Liệt kê các task còn lại.
4. **Lời khuyên hành động**.

---
**BÂY GIỜ, HÃY DỰA VÀO DỮ LIỆU THỰC TẾ ĐỂ VIẾT BẢN TIN CHO HÔM NAY:**
"""
        return self.generate_content(prompt, model=Config.GEMINI_MODEL_FLASH)

    def generate_voice_script(self, original_text):
        """Rewrites text for voice generation."""
        prompt = f"""
Bạn là biên tập viên phát thanh.
Thời gian: {self._get_vn_time()}
Nội dung bản tin:
---
{original_text}
---

Nhiệm vụ: Viết lại thành **KỊCH BẢN ĐỌC (Voice Script)** ngắn gọn, tự nhiên, bỏ emoji, bỏ markdown.
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
        # User requested 3-flash-preview/2.0-flash-exp for quiz
        return self.generate_content(prompt, model=Config.GEMINI_MODEL_PRO)
