# 🎓 UEH Notion Smart Assistant

Một hệ thống trợ lý học tập và quản lý công việc cá nhân thông minh, tích hợp chặt chẽ giữa **Notion**, **Telegram** và **AI**. Dự án này biến Notion của bạn từ một nơi lưu trữ thụ động thành một hệ thống chủ động: nhắc nhở ôn tập qua Spaced Repetition, sinh câu hỏi trắc nghiệm tự động bằng AI, và báo cáo công việc hằng ngày.

---

## 🚀 Các Tính Năng Chính

### 1. 📚 Góc Ôn Tập Khắc Sâu (Study Assistant - Telegram Web App)
- **Cơ chế Spaced Repetition:** Tự động quét trong kho Ghi chép Notion để tìm các bài học có trạng thái "Cần xem lại" hoặc lâu chưa ôn tập.
- **Trắc nghiệm AI:** Đọc nội dung bài học từ Notion và tự động soạn bộ đề trắc nghiệm (Multiple Choice) nhờ sức mạnh của AI.
- **Giao diện Web App mượt mà:** Trải nghiệm kiểm tra đúng/sai, xem giải thích chi tiết trực quan ngay bên trong ứng dụng Telegram (không cần mở trình duyệt ngoài).
- **Bộ nhớ đệm thông minh (Redis Cache):** Lưu lại đề đã sinh trong 14 ngày để tải siêu tốc độ và tiết kiệm Quota. Tích hợp nút "Tạo đề mới" để ép AI sinh câu hỏi khác.
- **Cập nhật trạng thái trực tiếp:** Sau khi hoàn thành, trạng thái nắm vững của bài học sẽ được tự động cập nhật ngược lại vào Notion (`Last Review At`).

### 2. 📅 Báo Cáo Công Việc Hằng Ngày (Daily Report)
- Tự động lấy danh sách công việc trong ngày từ Notion Database.
- Phân tích bằng AI: Sắp xếp công việc, lập kế hoạch và gửi báo cáo động lực qua tin nhắn Telegram.
- **Voice Briefing**: Gửi bản tin âm thanh (Voice Note) tóm tắt lịch trình để bạn nghe vào buổi sáng.

### 3. 🧠 Quản Lý Prompt Động (Prompt Database)
- Toàn bộ System Prompt (lời căn dặn AI) cho từng tính năng không bị hardcode trong mã nguồn mà được **lưu trực tiếp trên một bảng Notion riêng**. Dễ dàng thay đổi thái độ, giọng điệu, định dạng đầu ra của AI ngay trên Notion mà không cần động đến dòng code nào.

---

## 🏗 Kiến Trúc Hệ Thống

Dự án được xây dựng theo kiến trúc hiện đại, linh hoạt:

1. **Telegram Webhook (Cloudflare Workers):** Nhận và xử lý lệnh từ người dùng (`/study`, `/taskreport`). Điều hướng mở Web App hoặc kích hoạt Github Actions.
2. **API Backend (FastAPI trên Render):** Xử lý logic nghiệp vụ. Kết nối với Notion API, gọi AI, giao tiếp với Redis và trả dữ liệu JSON cho Frontend.
3. **Frontend (Cloudflare Pages):** Giao diện tĩnh (HTML/TailwindCSS/JS) của Telegram Web App hiển thị bộ câu hỏi trắc nghiệm.
4. **AI Engine (Custom Router):** Sử dụng chuẩn `OpenAI SDK` gọi qua hệ thống Router tùy chỉnh (ví dụ: 9Router trên HuggingFace), cho phép đổi mô hình AI (Claude, Gemini, ChatGPT) linh hoạt thông qua cấu hình.
5. **Database & Caching:** Dữ liệu lõi trên Notion, dữ liệu tạm (Cache) lưu trên Redis Server (Aiven).

---

## 💻 Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic, HTTPX.
- **Frontend:** HTML5, TailwindCSS (CDN), Vanilla JavaScript, Telegram Web App SDK.
- **AI Integration:** OpenAI Python SDK (kết nối Custom AI Router).
- **Caching:** Redis.
- **Hosting / Automation:** Render (Web API), Cloudflare (Pages & Workers), GitHub Actions.

---

## ⚙️ Cài Đặt & Triển Khai (Deployment)

### 1. Cấu hình biến môi trường (Environment Variables)
Bạn cần thiết lập các biến sau cho Backend (trên Render hoặc `.env` chạy local):

```env
# Notion
NOTION_TOKEN=secret_...
NOTION_DB_GHI_CHEP_ID=...
NOTION_DB_TASK=...
NOTION_PROMPT_DATABASE_ID=...

# Custom AI Router
USE_CUSTOM_AI=true
CUSTOM_AI_BASE_URL=https://khoitran1999-claude-server.hf.space/v1
CUSTOM_AI_API_KEY=sk-...
CUSTOM_AI_MODEL=my-combo

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Redis Cache
REDIS_URL=rediss://default:password@host:port
```

### 2. Triển khai Backend API (Render)
- Dự án đã có sẵn file `render.yaml`. 
- Kết nối GitHub Repository này với Render (kiểu Web Service) để tự động deploy FastAPI.
- (Mẹo: Cấu hình UptimeRobot gọi vào endpoint `/` mỗi 10 phút để giữ server không bị cold start).

### 3. Triển khai Frontend Web App (Cloudflare Pages)
- Vào Cloudflare Dashboard -> **Pages**.
- Kết nối kho GitHub, phần Build settings để `Build command` trống, `Build output directory` là `frontend`.
- (Quan trọng): Chỉnh biến `API_BASE_URL` trong file `frontend/app.js` thành URL Render API của bạn.

### 4. Thiết lập Telegram Bot (Cloudflare Workers)
- Tạo Worker mới trên Cloudflare, dán nội dung file `cloudflare_worker.js` vào.
- Trong Settings của Worker, thêm biến `WEBAPP_URL` là đường link Cloudflare Pages (bước 3).
- Cấu hình Webhook của Bot Telegram trỏ về Worker này.

---

## 🎮 Hướng Dẫn Sử Dụng

1. **Trên Telegram:** Mở cuộc trò chuyện với Bot của bạn.
2. Gõ `/start` hoặc bấm nút Menu.
3. **Ôn tập:** Chọn `/study` -> Bấm "Mở Góc Ôn Tập" -> Trải nghiệm Web App giải trắc nghiệm.
4. **Báo cáo:** Chọn `/taskreport` -> Nhận phân tích công việc hôm nay và tin nhắn thoại.

---

## 📂 Cấu Trúc Project

```text
UEH-Notion/
├── frontend/               # Nơi chứa Web App UI tĩnh (HTML/JS)
├── src/
│   ├── api/                # FastAPI (main.py định tuyến các request)
│   ├── jobs/               # Tác vụ định kỳ (Daily Report)
│   ├── services/           # Các class tương tác API (Notion, Telegram, AI, Study Logic)
│   └── config/             # Nơi tải biến môi trường settings
├── .github/workflows/      # Cấu hình tự động hóa GitHub Actions
├── cloudflare_worker.js    # Mã nguồn Webhook cho bot Telegram
├── render.yaml             # Cấu hình deploy tự động cho Render.com
├── requirements.txt        # Các thư viện Python cần thiết
└── README.md               # Tài liệu hướng dẫn
```

---
**Made with ❤️ for Productivity.**