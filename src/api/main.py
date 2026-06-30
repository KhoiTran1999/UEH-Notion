import re
import json
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from src.services.study_logic import get_candidates, generate_quiz, generate_quiz_stream, update_status, generate_quick_review
from src.jobs.daily_report import run_daily_report
from src.scripts.sync_timeline import run as run_sync_timeline
from src.services.timeline import get_timeline_summary, fetch_in_progress_tasks
from src.services.telegram import TelegramService
from src.config.settings import Config
from src.utils.logger import logger

UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)

app = FastAPI(title="Study Quiz API")

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuizRequest(BaseModel):
    topic_id: str
    force_refresh: bool = False

    @field_validator('topic_id')
    @classmethod
    def validate_topic_id(cls, v):
        if not UUID_PATTERN.match(v):
            raise ValueError(f'Invalid topic_id format: must be a valid UUID')
        return v

class StatusRequest(BaseModel):
    topic_id: str
    status: str | None = None

    @field_validator('topic_id')
    @classmethod
    def validate_topic_id(cls, v):
        if not UUID_PATTERN.match(v):
            raise ValueError(f'Invalid topic_id format: must be a valid UUID')
        return v

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    """Health check endpoint for UptimeRobot"""
    return {"status": "alive"}

@app.get("/api/study/candidates")
def api_get_candidates(force_refresh: bool = False):
    try:
        candidates = get_candidates(force_refresh=force_refresh)
        return {"candidates": candidates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/study/quiz")
def api_generate_quiz(request: QuizRequest):
    try:
        return StreamingResponse(
            generate_quiz_stream(request.topic_id, force_refresh=request.force_refresh),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/study/status")
def api_update_status(request: StatusRequest):
    success = update_status(request.topic_id, request.status)
    if success:
        return {"success": True, "message": "Status updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update status")

@app.get("/api/study/quick-review")
def api_quick_review():
    try:
        quiz_data = generate_quick_review()
        if not quiz_data:
            raise HTTPException(status_code=404, detail="No topics or questions found for quick review")
        return quiz_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ReportRequest(BaseModel):
    telegram_id: str | None = None

@app.post("/api/tasks/report")
def api_generate_report(request: ReportRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_daily_report)
    return {"success": True, "message": "Report generation started"}

@app.post("/api/tasks/sync-timeline")
def api_sync_timeline(request: ReportRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_sync_timeline)
    return {"success": True, "message": "Timeline sync started"}


def send_timeline(chat_id: str):
    """Send formatted timeline to Telegram chat."""
    telegram = TelegramService()
    try:
        msg = get_timeline_summary()
        telegram.send_message(msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"❌ Timeline send error: {e}")
        telegram.send_message("❌ Không thể tải timeline.")


def process_telegram_command(text: str, chat_id: str, background_tasks: BackgroundTasks):
    telegram = TelegramService()
    if text in ["/start", "/help"]:
        # Set Menu Button dynamically to open Web App directly
        telegram.set_menu_button(chat_id, "🎓 Ôn tập", Config.WEBAPP_URL)

        telegram.send_message(
            "✅ Bot đã sẵn sàng!\nChọn chức năng bên dưới hoặc gõ lệnh tương ứng:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📊 Báo cáo Task", "callback_data": "/taskreport"}],
                    [{"text": "📅 Xem Timeline", "callback_data": "/timeline"}],
                    [{"text": "🔄 Đồng bộ Timeline", "callback_data": "/timelinesync"}],
                    [{"text": "🎓 Ôn tập khắc sâu", "web_app": {"url": Config.WEBAPP_URL}}]
                ]
            }
        )
    elif text == "/taskreport":
        telegram.send_message("🚀 Đã nhận lệnh! Bắt đầu tạo báo cáo ngày cho bạn...")
        background_tasks.add_task(run_daily_report)
    elif text == "/timeline":
        telegram.send_message("📅 Đang tải timeline tasks...", disable_notification=True)
        background_tasks.add_task(send_timeline, chat_id)
    elif text == "/timelinesync":
        telegram.send_message("🔄 Đang đồng bộ timeline tasks... Vui lòng đợi trong giây lát.")
        background_tasks.add_task(run_sync_timeline)
    elif text == "/study":
        telegram.send_message(
            "📚 Mở góc ôn tập bằng Web App bên dưới nhé:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "Mở Góc Ôn Tập", "web_app": {"url": Config.WEBAPP_URL}}]
                ]
            }
        )
    elif text.startswith("/study_") or text.startswith("/mastered_") or text.startswith("/review_"):
        # Extract topic_id from the old format: /mastered_<short_id> or /review_<short_id>
        # Reconstruct UUID and send Web App deep link
        short_id = text.split("_", 1)[-1]
        if len(short_id) >= 32:
            reconstructed_id = f"{short_id[:8]}-{short_id[8:12]}-{short_id[12:16]}-{short_id[16:20]}-{short_id[20:]}"
            webapp_url = f"{Config.WEBAPP_URL}?topic_id={reconstructed_id}"
        else:
            webapp_url = Config.WEBAPP_URL
        telegram.send_message(
            "📚 Chức năng này đã được nâng cấp! Vui lòng sử dụng Web App bên dưới để ôn tập:",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📖 Mở Web App Ôn Tập", "web_app": {"url": webapp_url}}]
                ]
            }
        )

@app.post("/webhook/telegram")
@app.post("/webhook/telegram/")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        update = await request.json()
    except json.JSONDecodeError:
        return {"status": "error"}

    if "callback_query" in update:
        chat_id = str(update["callback_query"]["message"]["chat"]["id"])
        data = update["callback_query"]["data"]
        cb_id = update["callback_query"]["id"]

        TelegramService().answer_callback_query(cb_id)
        process_telegram_command(data, chat_id, background_tasks)
    elif "message" in update and "text" in update["message"]:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"]["text"].strip()
        process_telegram_command(text, chat_id, background_tasks)

    return {"status": "ok"}
