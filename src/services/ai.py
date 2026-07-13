import json
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from src.config.settings import Config
from src.utils.logger import logger

from src.services.prompt_service import PromptService
from src.services.telegram import TelegramService

class AIService:
    def __init__(self):
        self.prompt_service = PromptService()
        self.telegram = TelegramService()

        if Config.USE_CUSTOM_AI:
            self.client = OpenAI(
                base_url=Config.CUSTOM_AI_BASE_URL,
                api_key=Config.CUSTOM_AI_API_KEY
            )
        else:
            logger.error("❌ Legacy Gemini config used but google-genai is removed!")
            self.client = None

    def _get_vn_time(self):
        return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S")

    def generate_content(self, prompt, model=Config.MODEL_WORKER):
        if not self.client: return "AI Service Unavailable"

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                stream=False
            )

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from AI model")
            return content.strip()

        except Exception as e:
            logger.warning(f"⚠️ Generation failed for model {model}: {e}. Retrying with CUSTOM_AI_MODEL ({Config.CUSTOM_AI_MODEL})...")
            if model != Config.CUSTOM_AI_MODEL:
                try:
                    response = self.client.chat.completions.create(
                        model=Config.CUSTOM_AI_MODEL,
                        messages=[
                            {"role": "user", "content": prompt}
                        ],
                        stream=False
                    )
                    content = response.choices[0].message.content
                    if not content:
                        raise ValueError("Empty response from fallback model")
                    return content.strip()
                except Exception as fe:
                    logger.error(f"❌ Fallback generation also failed: {fe}")
                    self.telegram.send_message(f"❌ Lỗi khi gọi AI Router: {str(fe)}", disable_notification=True)
                    return f"Error: {str(fe)}"
            else:
                logger.error(f"❌ AI Generation Error: {e}")
                self.telegram.send_message(f"❌ Lỗi khi gọi AI Router: {str(e)}", disable_notification=True)
                return f"Error: {str(e)}"

    def _execute_tool(self, name, arguments):
        logger.info(f"[Tool] Execution: {name} with args {arguments}")
        try:
            if name == "fetch_notion_tasks":
                notion = NotionService()
                tasks = notion.get_tasks()
                return json.dumps(tasks, ensure_ascii=False)
            elif name == "fetch_notion_review_notes":
                notion = NotionService()
                notes = notion.get_review_notes()
                simplified_notes = []
                for note in notes:
                    title = "Unknown Note"
                    for key, val in note.get("properties", {}).items():
                        if val.get("type") == "title" and val["title"]:
                            title = val["title"][0]["plain_text"]
                            break
                    simplified_notes.append({
                        "id": note["id"],
                        "title": title
                    })
                return json.dumps(simplified_notes, ensure_ascii=False)
            elif name == "fetch_notion_page_content":
                page_id = arguments.get("page_id")
                if not page_id:
                    return "Error: page_id is required"
                notion = NotionService()
                content = notion.fetch_page_content(page_id)
                return json.dumps(content, ensure_ascii=False)
            elif name == "delegate_to_worker":
                instruction = arguments.get("instruction")
                if not instruction:
                    return "Error: instruction is required"
                result = self.generate_content(instruction, model=Config.MODEL_WORKER)
                return result
            else:
                return f"Error: Tool {name} not found"
        except Exception as e:
            logger.error(f"[Error] executing tool {name}: {e}")
            return f"Error executing tool: {str(e)}"

    def run_agent(self, system_prompt, user_prompt, model=Config.MODEL_BRAIN):
        """Runs MODEL_BRAIN as an agent with access to tools."""
        if not self.client: return "AI Service Unavailable"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "fetch_notion_tasks",
                    "description": "Lấy danh sách tất cả các nhiệm vụ (tasks) hiện tại chưa hoàn thành (trạng thái 'Not started' hoặc 'In progress') từ cơ sở dữ liệu Notion của người dùng. Trả về mảng các đối tượng chứa: tên nhiệm vụ, hạn chót, trạng thái, loại nhiệm vụ, và độ ưu tiên. Thích hợp dùng khi lập kế hoạch ngày hoặc báo cáo tiến độ."
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_notion_review_notes",
                    "description": "Lấy danh sách các bài học hoặc ghi chép học tập cần ôn tập (có trạng thái 'Cần xem lại' / '🔴 Cần xem lại') từ cơ sở dữ liệu Notion. Trả về mảng các trang chứa ID và tiêu đề trang. Dùng để xác định bài học nào cần làm trắc nghiệm ôn tập."
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fetch_notion_page_content",
                    "description": "Tải toàn bộ nội dung chi tiết của một trang Notion cụ thể (dựa vào page_id). Trả về danh sách các chuỗi văn bản (các khối nội dung) đã được định dạng cơ bản. Phải dùng tool này để lấy nội dung bài viết trước khi biên soạn câu hỏi trắc nghiệm hoặc phân tích sâu nội dung bài học.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "ID của trang Notion cần đọc nội dung."
                            }
                        },
                        "required": ["page_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_worker",
                    "description": "Ủy quyền/Giao việc cho mô hình phụ (MODEL_WORKER) để thực hiện các tác vụ xử lý văn bản cơ bản không đòi hỏi tư duy logic phức tạp hay đưa ra quyết định hệ thống. Các việc phù hợp: tóm tắt văn bản dài, viết kịch bản đọc giọng nói (voice script) từ bản tóm tắt, định dạng văn bản thành Markdown/HTML, dịch ngôn ngữ, trích xuất dữ liệu thô. KHÔNG giao cho Worker các việc như tự quyết định chọn bài học, tự phân tích chiến lược, hoặc tự tổng hợp kế hoạch ngày lớn.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "instruction": {
                                "type": "string",
                                "description": "Yêu cầu chi tiết, chỉ dẫn định dạng và đầy đủ dữ liệu/ngữ cảnh đầu vào để MODEL_WORKER thực hiện độc lập mà không cần hỏi lại."
                            }
                        },
                        "required": ["instruction"]
                    }
                }
            }
        ]

        max_steps = 10
        step = 0
        try:
            while step < max_steps:
                step += 1
                logger.info(f"[Agent] Loop Step {step} calling model...")
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    stream=False
                )

                choice = response.choices[0]
                message = choice.message
                messages.append(message)

                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments)
                        except Exception as e:
                            logger.error(f"Failed to parse tool arguments: {e}")
                            tool_args = {}

                        tool_result = self._execute_tool(tool_name, tool_args)
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": tool_result
                        })
                else:
                    content = message.content
                    if not content:
                        raise ValueError("Empty response from AI Agent")
                    return content.strip()

            logger.error("[Error] Agent exceeded max tool call steps.")
            return "Error: Agent loop exceeded maximum steps."

        except Exception as e:
            logger.error(f"[Error] Agent Execution Error: {e}")
            logger.warning(f"⚠️ Falling back to simple content generation using CUSTOM_AI_MODEL ({Config.CUSTOM_AI_MODEL})...")
            try:
                # Combine system prompt and user prompt
                fallback_prompt = f"{system_prompt}\n\n{user_prompt}"
                return self.generate_content(fallback_prompt, model=Config.CUSTOM_AI_MODEL)
            except Exception as fe:
                logger.error(f"❌ Fallback also failed: {fe}")
                self.telegram.send_message(f"❌ Lỗi khi chạy AI Agent và Fallback: {str(fe)}", disable_notification=True)
                return f"Error: {str(e)}"

    def analyze_tasks(self, tasks, db_options=None):
        """Generates the daily report analysis using prompts from Notion."""
        if not tasks:
            return "Chào buổi sáng! 🌞 Hôm nay bạn không có task nào phải làm. Hãy tận hưởng ngày nghỉ nhé! 🚀"

        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "task_planner")

        if not prompt_data:
            system_prompt = "Bạn là một Chuyên gia Quản trị năng suất."
            user_template = "Dữ liệu: {tasks_str}. Hãy phân tích."
            logger.warning("⚠️ Using fallback prompt for analyze_tasks")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]

        status_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Trạng thái", [])]) if db_options else ""
        type_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Loại nhiệm vụ", [])]) if db_options else ""
        priority_opts = ", ".join([f'"{opt}"' for opt in db_options.get("Độ ưu tiên", [])]) if db_options else ""

        tags_instruction = f"""
   • Trạng thái: {status_opts}
   • Loại nhiệm vụ: {type_opts}
   • Độ ưu tiên: {priority_opts}
""" if db_options else ""

        tasks_str = json.dumps(tasks, ensure_ascii=False, indent=2)

        user_prompt = user_template
        user_prompt = user_prompt.replace("{time}", self._get_vn_time())
        user_prompt = user_prompt.replace("{tasks_str}", tasks_str)
        user_prompt = user_prompt.replace("{tags}", tags_instruction)

        agent_system_prompt = (
            f"{system_prompt}\n\n"
            "QUY TẮC PHÂN CHIA VAI TRÒ:\n"
            "- Bạn là MODEL_BRAIN: Chịu trách nhiệm thực hiện các tác vụ tư duy, tính toán, lên kế hoạch, lập luận logic và sáng tạo.\n"
            "- Bạn có quyền điều phối MODEL_WORKER thông qua công cụ `delegate_to_worker` để xử lý các việc không cần suy nghĩ sâu như: tóm tắt văn bản thô, trích xuất thông tin đơn giản, định dạng lại dữ liệu thành Markdown/HTML, hoặc xử lý chuyển đổi chữ viết.\n"
            "Hãy giữ vai trò điều phối tối cao, tập trung tư duy chiến lược và giao phó triệt để việc cơ khí cho MODEL_WORKER."
        )

        return self.run_agent(system_prompt=agent_system_prompt, user_prompt=user_prompt, model=Config.MODEL_BRAIN)

    def summarize_timeline(self, timeline_data, is_raw_text=False):
        """Analyze timeline / raw text => structured deadline overview.

        Args:
            timeline_data: text string or list of block dicts
            is_raw_text: If True, timeline_data is already a raw text string, not structured dicts.
        """
        if not timeline_data:
            return "📭 Không có dữ liệu timeline để tổng hợp."

        vn_time = self._get_vn_time()

        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "timeline_summary")

        if not prompt_data:
            system_prompt = (
                "Bạn là trợ lý học tập thông minh tại UEH. Nhiệm vụ: phân tích dữ liệu tasks "
                "và đưa ra bản tổng quan deadline có cấu trúc.\n\n"
                "⚠️ Một block nội dung có thể chứa NHIỀU deadline khác nhau.\n"
                'VD: "Làm BT LMS. @Tomorrow 9:00 AM. Nộp bài LMS @Thursday 9:00 AM"\n'
                "→ Hãy TÁCH thành 2 việc riêng với deadline tương ứng.\n\n"
                "📅 Cách xử lý @date:\n"
                "- @Today = hôm nay, @Tomorrow = ngày mai\n"
                "- @Monday, @Tuesday... (hoặc @ThứHai, @ThứBa...) = thứ đó trong tuần này "
                "(nếu chưa qua) hoặc tuần sau\n"
                "- Suy luận và quy đổi ra ngày tháng cụ thể (dd/mm)\n\n"
                "Yêu cầu phân tích:\n"
                "1. Liệt kê từng deadline tìm được, kèm ngày/giờ cụ thể\n"
                "2. Sắp xếp theo thứ tự thời gian sớm → muộn\n"
                "3. Một dòng có nhiều deadline → tách riêng từng việc\n"
                "4. Nhóm theo tuần, đánh giá độ khẩn cấp\n"
                "5. Gợi ý thứ tự ưu tiên"
            )
            user_template = (
                "Thời gian hiện tại: {time}\n\n"
                "Dữ liệu tasks:\n{timeline_str}\n\n---\n"
                "Phân tích deadline và tổng hợp."
            )
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]

        system_prompt += (
            "\n\n⚠️ BẮT BUỘC VỀ ĐỊNH DẠNG (CHO TELEGRAM):\n"
            "- Trả lời bằng tiếng Việt.\n"
            "- CHỈ SỬ DỤNG HTML cơ bản được hỗ trợ bởi Telegram (<b>in đậm</b>, <i>in nghiêng</i>, <u>gạch chân</u>, <blockquote>trích dẫn</blockquote>, <code>monospaced</code>).\n"
            "- TUYỆT ĐỐI KHÔNG dùng Markdown (như **, *, #, ##).\n"
            "- TUYỆT ĐỐI KHÔNG dùng thẻ <br> hoặc <br/> để xuống dòng. Hãy dùng ký tự xuống dòng bình thường (\\n).\n"
            "- Hãy tổ chức timeline một cách khoa học bằng cách sử dụng cấu trúc khối blockquote:\n"
            "  + Dùng <b> để in đậm tiêu đề mốc thời gian lớn (Ví dụ: <b>📅 TUẦN NÀY</b>, <b>📅 TUẦN SAU</b>).\n"
            "  + Đặt toàn bộ các task thuộc mốc đó vào bên trong cặp thẻ <blockquote>...</blockquote>.\n"
            "  + Mỗi task đặt trên một dòng riêng biệt dạng: • <b>[Tên Môn Học]</b>: Nội dung task (<code>Ngày/Giờ</code>)\n"
            "- Sử dụng thẻ <code> để bọc ngày giờ (Ví dụ: <code>15/07 09:00</code>) giúp hiển thị nổi bật dạng nhãn (badge) dễ nhìn.\n"
            "- ⚠️ TUYỆT ĐỐI KHÔNG gộp nhiều task nhỏ hoặc nhiều deadline khác nhau lên trên cùng một dòng.\n"
            "- Ví dụ định dạng chuẩn cực đẹp:\n\n"
            "<b>📅 TUẦN NÀY:</b>\n"
            "<blockquote>• <b>Tài Chính Doanh Nghiệp</b>: Ghi bài Chương 5 (<code>15/07 09:00</code>)\n"
            "• <b>Lý Thuyết Tài Chính</b>: Thuyết trình nhóm (<code>16/07 09:00</code>)</blockquote>\n\n"
            "<b>📅 TUẦN SAU:</b>\n"
            "<blockquote>• <b>Kinh Tế Vĩ Mô</b>: Nộp bài tập cá nhân (<code>20/07 09:00</code>)</blockquote>"
        )

        if is_raw_text:
            timeline_str = str(timeline_data)
        elif isinstance(timeline_data, list):
            timeline_str = "\n".join(
                f"- {item.get('deadline', 'Không hạn')}: {item.get('clean_text', '')} ({item.get('task_name', '')})"
                for item in timeline_data
            )
        else:
            timeline_str = str(timeline_data)

        max_chars = 12000
        if len(timeline_str) > max_chars:
            timeline_str = timeline_str[-max_chars:]

        user_prompt = user_template.replace("{timeline_str}", timeline_str)
        user_prompt = user_prompt.replace("{time}", vn_time)

        final_prompt = f"{system_prompt}\n\n{user_prompt}"
        return self.generate_content(final_prompt, model=Config.MODEL_BRAIN)

    def generate_timeline_json(self, raw_data):
        """Analyze raw checklist data and return structured JSON timeline list."""
        vn_time = self._get_vn_time()
        system_prompt = (
            "Bạn là trợ lý phân tích dữ liệu deadline học tập tại UEH.\n"
            "Nhiệm vụ: phân tích dữ liệu tasks thô và trích xuất thành danh sách JSON có cấu trúc gồm các deadline chi tiết.\n\n"
            "⚠️ Hãy TÁCH một task có nhiều deadline thành các dòng/đối tượng JSON riêng biệt.\n"
            "Quy đổi các mốc thời gian dạng @Today, @Tomorrow, @Monday thành ngày tháng cụ thể (ví dụ: '15/07 09:00') dựa theo mốc hiện tại.\n\n"
            "Đầu ra PHẢI là một mảng JSON duy nhất (không có bất kỳ từ giải thích nào khác bên ngoài), mỗi đối tượng chứa:\n"
            "- \"date\": Ngày tháng hiển thị rút gọn (ví dụ: \"21/07\" hoặc \"21/07 09:00\").\n"
            "- \"course\": Tên môn học viết ngắn gọn hoặc tên nhóm task (ví dụ: \"Tài Chính Doanh Nghiệp\").\n"
            "- \"content\": Nội dung chi tiết của deadline đó.\n"
            "- \"urgency\": Mức độ khẩn cấp (\"high\", \"normal\", hoặc \"low\") dựa vào thời gian hạn chót.\n"
            "- \"weekday\": Tên thứ rút gọn (ví dụ: \"Thứ 3\" hoặc \"T2\").\n"
            "- \"page_id\": ID trang Notion lấy từ thông tin (PageID: ...) trong tiêu đề của môn học tương ứng.\n"
            "\n"
            "Ví dụ mẫu đầu ra:\n"
            "[\n"
            "  {\n"
            "    \"date\": \"15/07 09:00\",\n"
            "    \"course\": \"Tài Chính Doanh Nghiệp\",\n"
            "    \"content\": \"Ghi bài Chương 5\",\n"
            "    \"urgency\": \"high\",\n"
            "    \"weekday\": \"T4\",\n"
            "    \"page_id\": \"d3b07384d113458db7be572e946059d2\"\n"
            "  }\n"
            "]"
        )
        user_prompt = f"Mốc thời gian hiện tại: {vn_time}\n\nDữ liệu thô:\n{raw_data}\n\nHãy trả về mảng JSON timeline:"
        return self.generate_content(f"{system_prompt}\n\n{user_prompt}", model=Config.MODEL_WORKER)


    def generate_voice_script(self, original_text):
        """Rewrites text for voice generation using Notion prompt."""
        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "voice_script")

        if not prompt_data:
            return "Error: Could not fetch voice script prompt."

        system_prompt = prompt_data["system_prompt"]
        user_template = prompt_data["user_template"]

        final_prompt = f"{user_template}\n\n{system_prompt}"
        final_prompt = final_prompt.replace("{time}", self._get_vn_time())
        final_prompt = final_prompt.replace("{user_label}", "Khôi")
        final_prompt = final_prompt.replace("{original_text}", original_text)

        # Voice script generation is a simple text rewriting job - run it directly on MODEL_WORKER
        return self.generate_content(final_prompt, model=Config.MODEL_WORKER)

    def generate_quiz(self, content):
        """Generates quiz questions from review notes using Notion prompt."""
        if not content: return "Nội dung trống."

        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "study_assistant")

        if not prompt_data:
            system_prompt = f"Bạn là một Chuyên gia Giáo dục và Trợ lý Học tập Thông minh. Hãy tạo chính xác 15 câu hỏi trắc nghiệm từ nội dung bên dưới."
            user_template = "--- NỘI DUNG GHI CHÉP ---\n{content}\n-------------------------"
            logger.warning("⚠️ Using fallback prompt for generate_quiz")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]

        additional_instructions = f"""
        QUAN TRỌNG VỀ SỐ LƯỢNG:
        - Phải tạo chính xác 15 câu hỏi trắc nghiệm.

        QUAN TRỌNG VỀ ĐỊNH DẠNG TOÁN HỌC:
        1. SỬ DỤNG định dạng LaTeX (kẹp giữa ký tự $ cho công thức cùng dòng và $$ cho công thức nằm riêng dòng) để viết các công thức toán học, tài chính, thống kê, ma trận phức tạp.
        2. Đảm bảo cú pháp LaTeX chính xác và chuẩn chỉnh để bộ thư viện KaTeX có thể render được.
        3. Đối với các biểu thức cực kỳ đơn giản, có thể dùng ký tự thường hoặc Unicode nếu muốn, nhưng ưu tiên sử dụng LaTeX ($...$) cho các công thức, ký hiệu toán học để hiển thị chuyên nghiệp nhất.
        """

        user_prompt = user_template.replace("{content}", content)
        agent_system_prompt = (
            f"{system_prompt}\n\n{additional_instructions}\n\n"
            "QUY TẮC PHÂN CHIA VAI TRÒ:\n"
            "- Bạn là MODEL_BRAIN: Tập trung hoàn toàn vào việc tư duy, phân tích kiến thức sâu, tính toán bài tập, sáng tạo các câu hỏi trắc nghiệm chất lượng.\n"
            "- Bạn có công cụ `delegate_to_worker` để sai khiến MODEL_WORKER làm việc cơ học như: trích xuất từ khóa thô từ bài học, định dạng lại công thức hoặc cấu trúc đề thi thô, hay tóm tắt sơ bộ.\n"
            "Hãy giữ vai trò thiết kế và tư duy logic, giao phó việc định dạng hoặc xử lý dữ liệu thô cho MODEL_WORKER."
        )

        return self.run_agent(system_prompt=agent_system_prompt, user_prompt=user_prompt, model=Config.MODEL_BRAIN)

    def review_quiz(self, raw_quiz, content):
        """Reviews and self-corrects the generated quiz using Notion prompt or a robust fallback."""
        if not raw_quiz or not content: return raw_quiz

        prompt_data = self.prompt_service.get_prompt("UEH-Notion", "study_assistant_review")

        if not prompt_data:
            system_prompt = f"""Bạn là một Chuyên gia Giáo dục và Trợ lý Kiểm định Chất lượng Học tập. Nhiệm vụ của bạn là nhận vào nội dung bài học gốc (ghi chép) và danh sách câu hỏi trắc nghiệm đã được sinh ra từ nội dung này.
Hãy thực hiện kiểm tra kỹ lượng danh sách câu hỏi này theo các tiêu chuẩn nghiêm ngặt sau:
1. Số lượng câu hỏi: Phải đủ chính xác 15 câu hỏi trắc nghiệm. Nếu thiếu hoặc thừa, hãy điều chỉnh để có đúng 15 câu.
2. Sự chính xác và phù hợp: Tất cả các câu hỏi phải dựa trên thực tế từ nội dung ghi chép, không được tự bịa ra thông tin không có trong tài liệu.
3. Chất lượng câu hỏi: Câu hỏi phải rõ ràng, phân biệt được độ khó, không mập mờ, không bị lỗi hành văn, lỗi dịch thuật hay lỗi logic. Các đáp án sai phải là các đáp án nhiễu hợp lý (distractors), không được quá ngớ ngẩn. Chỉ có duy nhất một đáp án đúng.
4. Định dạng Toán học & Công thức:
   - Tất cả các công thức toán học, thống kê, ký hiệu tài chính (như NPV, IRR, độ lệch chuẩn, kỳ vọng, mũ, phân số, ma trận, chỉ số dưới/trên...) PHẢI được định dạng chuẩn bằng LaTeX, đặt trong cặp dấu $ cho công thức cùng dòng (inline) và $$ cho công thức nằm riêng dòng (block).
   - Đảm bảo cú pháp LaTeX chính xác và chuẩn chỉnh để thư viện KaTeX có thể hiển thị thành công. Ví dụ: viết $x_i$ thay vị xi, viết \\sigma thay vì sigma, viết \\frac{{a}}{{b}} thay vì a/b khi viết công thức phức tạp.
5. Định dạng JSON Đầu ra:
   - Đầu ra của bạn PHẢI là một mảng JSON chứa chính xác các câu hỏi theo đúng định dạng sau, KHÔNG được chứa bất kỳ văn bản giải thích, markdown nào bên ngoài khối JSON. Chỉ trả về một mảng JSON hợp lệ duy nhất:
   [
     {{
       "q": "Câu hỏi thứ nhất chứa nội dung câu hỏi...?",
       "options": [
         "A. Lựa chọn A",
         "B. Lựa chọn B",
         "C. Lựa chọn C",
         "D. Lựa chọn D"
       ],
       "correct": 0,
       "explanation": "Giải thích chi tiết lý do tại sao đáp án đó đúng dựa trên ghi chép..."
     }},
     ...
   ]"""
            user_template = """--- NỘI DUNG GHI CHÉP GỐC ---
{content}
-----------------------------

--- DANH SÁCH CÂU HỎI CẦN KIỂM DUYỆT (RAW QUIZ JSON) ---
{raw_quiz}
-------------------------------------------------------

Hãy đánh giá, chỉnh sửa, bổ sung và xuất ra danh sách 15 câu hỏi trắc nghiệm đã được chuẩn hóa và sửa lỗi hoàn toàn dưới dạng mảng JSON duy nhất."""
            model = Config.MODEL_WORKER
            logger.warning("⚠️ Using fallback prompt for review_quiz")
        else:
            system_prompt = prompt_data["system_prompt"]
            user_template = prompt_data["user_template"]
            model = Config.MODEL_WORKER

        final_prompt = f"{user_template}\n\n{system_prompt}"
        final_prompt = final_prompt.replace("{content}", content)
        final_prompt = final_prompt.replace("{raw_quiz}", raw_quiz)

        return self.generate_content(final_prompt, model=model)

    def final_review_quiz(self, questions_json, content):
        """Final review and polish of merged quiz questions: use MODEL_BRAIN to fix errors and enhance quality."""
        if not questions_json or not content: return questions_json

        system_prompt = """Bạn là Chuyên gia Kiểm định Chất lượng Học tập — MODEL_BRAIN.

Nhiệm vụ của bạn là duyệt danh sách câu hỏi trắc nghiệm đã được tạo tự động, và sử dụng tư duy phản biện để:

1. KIỂM TRA & SỬA LỖI:
   - Mỗi câu hỏi phải có đúng 4 đáp án A, B, C, D
   - Chỉ có duy nhất 1 đáp án đúng mỗi câu
   - Sửa lỗi chính tả, lỗi hành văn, lỗi logic
   - Sửa lỗi LaTeX (đảm bảo KaTeX render được)

2. CẢI THIỆN CHẤT LƯỢNG (tư duy BRAIN):
   - Làm cho câu hỏi rõ ràng, sắc bén hơn
   - Nếu đáp án nhiễu quá ngớ ngẩn hoặc dễ đoán, hãy thay bằng đáp án nhiễu tinh vi hơn
   - Đảm bảo câu hỏi không bị mập mờ, có duy nhất một cách hiểu đúng
   - Nếu cần, hãy bổ sung hoặc nâng cấp explanation để giải thích sâu hơn

3. PHẠM VI:
   - LUÔN dựa trên nội dung bài học. KHÔNG được thêm kiến thức bên ngoài.
   - KHÔNG bỏ qua câu hỏi nào — giải quyết tất cả.
   - Đầu ra PHẢI là một mảng JSON hợp lệ duy nhất, KHÔNG có text bên ngoài.

QUY TẮC PHÂN CHIA VAI TRÒ:
- Bạn là MODEL_BRAIN: Tập trung hoàn toàn vào việc tư duy phản biện, đánh giá chất lượng và cải thiện câu hỏi.
- Bạn có công cụ `delegate_to_worker` để sai khiến MODEL_WORKER làm việc cơ học như: định dạng lại JSON, kiểm tra cú pháp chuỗi, chuẩn hoá LaTeX đơn giản. Hãy giao phó việc cơ khí, tập trung tư duy sáng tạo.
"""
        user_prompt = f"""--- NỘI DUNG BÀI HỌC ---
{content}
-------------------------

--- DANH SÁCH CÂU HỎI CẦN KIỂM DUYỆT ---
{questions_json}
-----------------------------------------

Hãy kiểm tra, sửa lỗi và nâng cấp chất lượng toàn bộ danh sách. Trả về mảng JSON duy nhất."""

        return self.run_agent(system_prompt=system_prompt, user_prompt=user_prompt, model=Config.MODEL_BRAIN)
