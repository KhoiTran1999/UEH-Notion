# 🎓 UEH Notion Smart Assistant

**UEH Notion Smart Assistant** là hệ thống trợ lý học tập và quản lý công việc cá nhân tự động hoá toàn diện, kết hợp giữa **Notion** (lưu trữ dữ liệu), **Telegram** (giao diện tương tác & thông báo), **Redis** (caching siêu tốc & đồng bộ tiến trình) và **AI Router** (phân tích, trắc nghiệm, tóm tắt & Text-to-Speech).

---

## 🌟 Tính Năng Chính

### 1. 📚 Trợ Lý Ôn Tập Thông Minh (Study Assistant - Telegram Web App)
- **Spaced Repetition (Lặp lại ngắt quãng):** Tự động lọc các bài học/ghi chép cần xem lại dựa trên trạng thái và mốc thời gian `Last Review At` từ Notion.
- **Tự Động Tạo Đề Trắc Nghiệm Bằng AI:**
  - Phân tích nội dung ghi chép (chia luồng AI song song xử lý bài dài).
  - Tự động sinh bộ câu hỏi trắc nghiệm 4 lựa chọn (A, B, C, D) kèm giải thích chi tiết.
  - Hỗ trợ công thức Toán học / Tài chính chuẩn **KaTeX / LaTeX** hiển thị sắc nét.
  - Chế độ **Ôn tập nhanh (Quick Review)** tổng hợp ngẫu nhiên theo môn học.
- **Lưu Tiến Trình & Caching (Redis):**
  - Lưu và khôi phục tiến trình làm bài dở dang theo từng chủ đề và người dùng.
  - Cache đề thi trong 14 ngày giúp tải tức thì, tiết kiệm chi phí AI; hỗ trợ nút xóa cache trực tiếp trên từng thẻ bài học.
- **Trải Nghiệm Web App Đỉnh Cao:**
  - Đồng hồ đếm giờ làm bài, thanh tiến trình trực quan.
  - Đánh dấu câu hỏi cần xem lại, xem lại danh sách câu làm sai và làm lại câu sai.
  - Đồng bộ 2 chiều: Tự động cập nhật trạng thái mức độ nắm vững và `Last Review At` ngược lại Notion.

### 2. 📅 Theo Dõi Timeline & Deadline (Task Timeline)
- **Trích xuất Task đang thực hiện (`In Progress`):** Đọc nội dung block, checkbox, to-do list và các mention ngày tháng (`@Today`, `@Tomorrow`, `@ThứHai`, v.v.) trong Notion.
- **Xem Timeline qua Telegram Chat (`/timeline`):** AI phân tích, tổng hợp tiến độ và định dạng báo cáo HTML trực quan gửi thẳng vào chat.
- **Giao Diện Timeline trên Web App (`?view=timeline`):** Xem danh sách deadline dạng trực quan, hỗ trợ bộ lọc theo môn học, tháng và ngày.

### 3. 🎙️ Báo Cáo Công Việc Hàng Ngày & Bản Tin Giọng Nói (Daily Voice Briefing)
- **AI Task Prioritization:** Lọc và phân loại các công việc trong ngày theo độ ưu tiên, viết bản tin tổng kết tạo động lực.
- **Bản tin Voice Note (TTS):** Tự động chuyển đổi nội dung báo cáo thành file âm thanh MP3 (hỗ trợ chunking tránh giới hạn ký tự) và gửi qua Telegram dưới dạng tin nhắn thoại mỗi sáng.

### 4. 🧠 Quản Lý Prompt Linh Hoạt (Dynamic Prompt Database)
- Toàn bộ Prompt và Persona của AI được quản lý trên Notion Database riêng biệt, dễ dàng tinh chỉnh trực tiếp mà không cần sửa mã nguồn hoặc deploy lại.

---

## 🏗️ Kiến Trúc Hệ Thống

```text
[ Notion Databases ] ── (Ghi chép / Tasks / Prompts)
        │
        ▼
[ FastAPI Backend (Render) ] ── [ Redis Cache ] (Lưu trữ đề thi, tiến trình, lock)
   │        │            │
   │        │            └── [ AI Engine / TTS Router ] (Claude / GPT / Gemini)
   │        │
   │        ▼
   │   [ Telegram Bot ] ── (Thông báo, Voice Note, Timeline, Menu WebApp)
   │
   ▼
[ Frontend Web App (Cloudflare Pages) ] ── (Giao diện trắc nghiệm KaTeX, Timeline)
```

---

## 💻 Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2, HTTPX, Redis (`redis-py`).
- **Frontend:** HTML5, Vanilla JavaScript (ES6+), Tailwind CSS (CDN), KaTeX, Telegram WebApp SDK.
- **AI & Voice:** OpenAI Python SDK (Custom Router / 9Router / HuggingFace Spaces), Gemini API (Fallback / Legacy TTS).
- **Cơ sở dữ liệu:** Notion API (`2025-09-03`), Redis (Aiven / Upstash).
- **Hạ tầng & CI/CD:** Render (Web Service), Cloudflare Pages (Frontend Hosting), GitHub Actions.

---

## 📂 Cấu Trúc Thư Mục

```text
UEH-Notion/
├── frontend/                   # Frontend Telegram Web App
│   ├── index.html              # Giao diện chính (Quiz, Results, Timeline)
│   └── app.js                  # State management, API client, KaTeX rendering
├── src/
│   ├── api/
│   │   └── main.py             # FastAPI router, webhook handler, background tasks
│   ├── config/
│   │   └── settings.py         # Quản lý biến môi trường & validation
│   ├── jobs/
│   │   ├── daily_report.py     # Job lập báo cáo ngày & gửi Voice note
│   │   ├── study_assistant.py  # Background job ôn tập
│   │   └── update_study_status.py # Đồng bộ trạng thái về Notion
│   ├── services/
│   │   ├── ai.py               # Tương tác với AI Router & quản lý model
│   │   ├── notion.py           # Notion API client (lấy task, note, blocks)
│   │   ├── prompt_service.py   # Lấy prompt động từ Notion DB
│   │   ├── study_logic.py      # Xử lý tạo đề quiz, streaming, cache & progress
│   │   ├── telegram.py         # Telegram Bot client & menu handler
│   │   ├── timeline.py         # Xử lý timeline, parse mention ngày & phân tích
│   │   └── voice.py            # Text-to-Speech & audio chunking
│   └── utils/
│       ├── block_parser.py     # Parser bóc tách Notion blocks sang text
│       ├── cache.py            # Redis client & helper TTL
│       ├── katex_validator.py  # KaTeX math cleaner & validation
│       └── logger.py           # Logging chuẩn hóa
├── render.yaml                 # Cấu hình deploy Render Blueprint
├── requirements.txt            # Danh sách thư viện Python
└── README.md
```

---

## ⚙️ Cài Đặt & Triển Khai

### 1. Biến Môi Trường (`.env`)

Tạo file `.env` tại thư mục gốc dựa theo cấu hình mẫu:

```env
# 1. Notion API
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PROMPT_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxx # (Tùy chọn: token phụ cho Prompt DB)
NOTION_DB_GHI_CHEP_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DB_TASK=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PROMPT_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_VERSION=2025-09-03

# 2. AI Router (Chuẩn OpenAI)
USE_CUSTOM_AI=true
CUSTOM_AI_BASE_URL=https://your-custom-ai-router.hf.space/v1
CUSTOM_AI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CUSTOM_AI_MODEL=claude-3-5-sonnet
REASONING_EFFORT=high
CUSTOM_AI_VOICE_MODEL=google-tts/vi

# 3. Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ
TELEGRAM_CHAT_ID=123456789
WEBAPP_URL=https://ueh-notion.pages.dev

# 4. Redis Cache
REDIS_URL=rediss://user:password@host:port
```

### 2. Chạy Cục Bộ (Local Development)

```bash
# 1. Tạo và kích hoạt môi trường ảo
python -m venv .venv
source .venv/bin/activate  # Trên Windows: .venv\Scripts\activate

# 2. Cài đặt dependencies
pip install -r requirements.txt

# 3. Khởi chạy FastAPI server
uvicorn src.api.main:app --reload --port 8000
```

### 3. Triển Khai Lên Cloud

1. **Backend (Render):**
   - Tạo Web Service từ repo GitHub (hoặc dùng `render.yaml`).
   - Thiết lập các biến môi trường tương ứng trong mục Environment.
2. **Frontend (Cloudflare Pages):**
   - Connect Git repository vào Cloudflare Pages.
   - Build output directory: `frontend` (Build command để trống).
   - Cập nhật `API_BASE_URL` trong `frontend/app.js` và cấu hình `WEBAPP_URL` trên Backend.
3. **Cài Đặt Telegram Webhook:**
   ```text
   https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<RENDER_API_URL>/webhook/telegram
   ```

---

## 📱 Lệnh Telegram Bot

| Lệnh | Mô tả |
| :--- | :--- |
| `/start` hoặc `/help` | Khởi động bot, hiển thị menu chính và cập nhật nút Menu WebApp |
| `/timeline` | Tải và gửi timeline công việc/deadline dạng HTML tóm tắt |
| `/study` | Mở nhanh Web App góc ôn tập trắc nghiệm |
| `/taskreport` | Kích hoạt tạo báo cáo công việc và gửi bản tin âm thanh Voice Note |

---

**Made with ❤️ for High Productivity & Academic Excellence.**
