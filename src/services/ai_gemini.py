"""Gemini direct API integration for timeline summarization."""
import json
from google import genai
from src.config.settings import Config
from src.utils.logger import logger


def summarize_timeline(all_deadline_blocks):
    """Use Gemini to summarize raw timeline blocks into an intelligent overview."""
    if not all_deadline_blocks:
        return "📭 Không có dữ liệu timeline để tổng hợp."

    client = genai.Client(api_key=Config.GEMINI_API_KEY)

    # Build clean data for AI
    data_lines = []
    for pb in all_deadline_blocks:
        deadline = pb.get("deadline", "Không hạn")
        text = pb.get("clean_text", "")
        task = pb.get("task_name", "")
        data_lines.append(f"- Deadline {deadline}: {text} (Task: {task})")

    data_str = "\n".join(data_lines)

    prompt = f"""Bạn là trợ lý học tập thông minh của sinh viên UEH.
Dưới đây là danh sách các nhiệm vụ (tasks) đang thực hiện, sắp xếp theo deadline từ sớm nhất đến muộn nhất.

--- DATA ---
{data_str}
---

Hãy phân tích và tổng hợp thành một bản overview ngắn gọn (dưới 300 từ), giúp sinh viên:
1. Nhìn tổng quan khối lượng công việc trong tuần này vs tuần sau vs tháng sau
2. Nhận xét deadline nào紧迫 nhất cần ưu tiên
3. Gợi ý thứ tự ưu tiên thực hiện

Định dạng bằng Markdown cho Telegram. Dùng emoji để phân loại. Trả lời bằng tiếng Việt. KHÔNG giải thích dài dòng."""

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini timeline summarization failed: {e}")
        return "⚠️ Không thể tạo bản tổng hợp AI lúc này."
