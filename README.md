# 🎓 UEH Notion Smart Assistant

**UEH Notion Smart Assistant** là một hệ thống trợ lý học tập và quản lý công việc cá nhân toàn diện. Dự án kết hợp chặt chẽ giữa **Notion** (lưu trữ), **Telegram** (giao tiếp) và **Trí tuệ Nhân tạo - AI** (phân tích & sinh nội dung), giúp biến kho dữ liệu thụ động của bạn thành một cỗ máy chủ động nhắc nhở và tối ưu hóa năng suất.

---

## 🌟 Các Tính Năng Nổi Bật

### 1. 📚 Góc Ôn Tập Khắc Sâu (Study Assistant - Telegram Web App)
- **Thuật toán Spaced Repetition:** Hệ thống tự động quét Notion để tìm các bài học có trạng thái "Cần xem lại" hoặc đã lâu chưa ôn tập (dựa trên trường `Last Review At`).
- **Trắc nghiệm Đa lựa chọn (Multiple Choice) bằng AI:** Đọc nội dung ghi chép và tự động biên soạn bộ câu hỏi trắc nghiệm (A, B, C, D) sinh động.
- **Giao diện Telegram Web App Hiện đại:**
  - Trải nghiệm mượt mà ngay trong Telegram, không cần mở trình duyệt ngoài.
  - Thiết kế dạng thẻ (Card) với hiệu ứng animation phong cách Apple (bouncy, fade-in).
  - Phản hồi trực quan: Đổi màu gradient (Xanh/Đỏ), hiển thị icon (✅/❌) và giải thích chi tiết ngay khi chọn đáp án.
  - Hỗ trợ di chuyển Tới/Lùi (Next/Previous) có ghi nhớ lịch sử chọn đáp án.
- **Caching Thông minh (Redis):** Đề thi được sinh ra sẽ lưu vào bộ nhớ đệm trong **14 ngày**. Giúp tải đề cực nhanh và tiết kiệm Quota AI. Hỗ trợ nút "Bỏ qua Cache" để ép AI tạo đề hoàn toàn mới.
- **Đồng bộ hóa 2 chiều:** Khi hoàn thành bài ôn tập, trạng thái mức độ hiểu bài sẽ được đồng bộ ngược lại vào Notion của bạn.

### 2. 📅 Báo Cáo Công Việc Hằng Ngày (Daily Task Report)
- **Trích xuất thông minh:** Lọc các công việc (Task) trong ngày từ cơ sở dữ liệu Notion.
- **AI Lập Kế Hoạch:** Phân tích, phân loại công việc theo mức độ ưu tiên và viết một bản tóm tắt tạo động lực.
- **Bản tin Giọng nói (Voice Briefing):** Sử dụng công nghệ Text-to-Speech (TTS) đọc báo cáo thành file âm thanh MP3 và gửi thẳng qua Telegram như một đoạn tin nhắn thoại (Voice Note) để bạn nghe mỗi sáng. Xử lý thông minh việc băm nhỏ văn bản (chunking) để vượt qua giới hạn độ dài của các API giọng nói.

### 3. 🧠 Quản Lý Prompt Linh Hoạt (Prompt Database)
- Không có dòng lệnh ép buộc (hardcode prompt) nào trong mã nguồn. Toàn bộ tính cách, ngữ cảnh của AI được lưu trên một bảng (Database) riêng tại Notion.
- Bạn có thể tùy ý sửa đổi cách AI phản hồi (giọng điệu, định dạng JSON) bằng cách chỉnh sửa trực tiếp trên Notion.

---

## 🏗 Kiến Trúc Hệ Thống

Dự án được cấu trúc theo mô hình phân tán, hoạt động 24/7 trên Cloud:

1. **API Backend (FastAPI - Hosted trên Render):** 
   - Đóng vai trò là "Bộ não trung tâm".
   - Nhận Webhook trực tiếp từ Telegram.
   - Kết nối với Notion API để đọc/ghi dữ liệu.
   - Giao tiếp với AI Router và Redis.
2. **Frontend (Cloudflare Pages):**
   - Lưu trữ giao diện tĩnh (HTML, JS, CSS/Tailwind) cho Web App Trắc nghiệm.
   - Giao tiếp trực tiếp với Backend API.
3. **AI Engine (Custom OpenAI-Compatible Router):**
   - Sử dụng thư viện `OpenAI SDK` để linh hoạt kết nối với các Router AI tùy chỉnh (như 9Router trên HuggingFace).
   - Dễ dàng thay đổi các mô hình ngôn ngữ (Claude, Gemini, ChatGPT) chỉ bằng cấu hình môi trường mà không cần sửa code.
4. **Cơ sở dữ liệu & Caching:**
   - **Notion:** Cơ sở dữ liệu chính.
   - **Redis (Aiven):** Lưu trữ bộ đệm siêu tốc cho các bài trắc nghiệm.

---

## 💻 Tech Stack

- **Ngôn ngữ:** Python 3.12, JavaScript (ES6+), HTML5.
- **Backend Framework:** FastAPI, Uvicorn, Pydantic, HTTPX.
- **Frontend UI:** Tailwind CSS (qua CDN), Telegram Web App SDK.
- **AI Integration:** OpenAI Python SDK (hỗ trợ cả Chat Completions & TTS).
- **Lưu trữ / CI-CD:** Render (Web Service), Cloudflare Pages (Frontend), GitHub.

---

## ⚙️ Hướng Dẫn Cài Đặt & Triển Khai (Deployment)

### Bước 1: Cấu hình Biến Môi Trường (Environment Variables)
Bạn cần thiết lập các biến sau (có thể lưu trong file `.env` khi chạy local hoặc trên mục Environment Variables của Render):

```env
# 1. Cấu hình Notion
NOTION_TOKEN=secret_xxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DB_GHI_CHEP_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_DB_TASK=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NOTION_PROMPT_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 2. Cấu hình AI Router (Chuẩn OpenAI)
USE_CUSTOM_AI=true
CUSTOM_AI_BASE_URL=https://khoitran1999-claude-server.hf.space/v1
CUSTOM_AI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CUSTOM_AI_MODEL=my-combo
CUSTOM_AI_VOICE_MODEL=google-tts/vi

# 3. Cấu hình Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ
TELEGRAM_CHAT_ID=123456789

# 4. Cấu hình Redis Cache
REDIS_URL=rediss://user:password@host:port

# 5. Cấu hình Frontend
WEBAPP_URL=https://ueh-notion.pages.dev
```

### Bước 2: Triển khai Backend API (Render)
1. Truy cập [Render.com](https://render.com), tạo một **Web Service** mới và kết nối với Repository GitHub của bạn.
2. Render sẽ tự động nhận diện file `render.yaml` trong mã nguồn và tự thiết lập các thông số (Build command, Start command).
3. Điền các Biến môi trường ở Bước 1 vào Render.
4. Triển khai. URL API của bạn sẽ có dạng `https://ueh-notion.onrender.com`.
*(Mẹo: Dự án đã có sẵn Endpoint `/` hỗ trợ cả `GET` và `HEAD`. Hãy cấu hình UptimeRobot gọi vào endpoint này mỗi 10 phút để server không bị rơi vào trạng thái ngủ đông).*

### Bước 3: Triển khai Frontend Web App (Cloudflare Pages)
1. Truy cập Dashboard Cloudflare -> **Workers & Pages** -> Chọn tab **Pages** -> **Connect to Git**.
2. Kết nối tới Repository này.
3. Ở phần **Build settings**:
   - Framework preset: `None`
   - Build command: *(Để trống)*
   - Build output directory: `frontend`
4. Deploy để lấy URL Frontend (ví dụ: `https://ueh-notion.pages.dev`).
5. Vào file `frontend/app.js` trong mã nguồn, đảm bảo biến `API_BASE_URL` trỏ đúng về URL Render API của bạn ở Bước 2. Cập nhật URL Frontend này vào biến `WEBAPP_URL` trên Render.

### Bước 4: Thiết lập Webhook Telegram
Để Bot Telegram biết nơi gửi tin nhắn đến, bạn mở Terminal hoặc trình duyệt và chạy đường dẫn sau:
```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<RENDER_API_URL>/webhook/telegram
```
*Lưu ý thay các thông số bằng Token Bot và Link Render của bạn.*

---

## 🎮 Cách Sử Dụng

Mở ứng dụng Telegram, tìm đến Bot của bạn và sử dụng các lệnh:
- `/start` hoặc `/help`: Hiển thị Menu chức năng tương tác (Inline Keyboard).
- `/study`: Gọi tính năng Góc Ôn Tập. Bot sẽ gửi kèm một nút bấm để mở **Web App Trắc Nghiệm** ngay trên màn hình.
- `/taskreport`: Trích xuất công việc hôm nay, yêu cầu AI phân tích và gửi báo cáo phân tích kèm tin nhắn âm thanh (Voice Note).

---

## 📂 Cấu Trúc Mã Nguồn

```text
UEH-Notion/
├── frontend/               # Mã nguồn Frontend (Web App)
│   ├── app.js              # Logic xử lý giao diện Trắc nghiệm, gọi API
│   └── index.html          # Cấu trúc UI HTML/TailwindCSS
├── src/
│   ├── api/                
│   │   └── main.py         # FastAPI App, Định tuyến API & Webhook
│   ├── config/             
│   │   └── settings.py     # Quản lý và xác thực Biến môi trường
│   ├── jobs/               
│   │   └── daily_report.py # Tác vụ lập báo cáo ngày
│   └── services/           
│       ├── ai.py           # Kết nối Custom AI Router (Text & Analyze)
│       ├── notion.py       # Tương tác Notion API
│       ├── prompt_service.py # Quản lý Prompt động từ Notion DB
│       ├── study_logic.py  # Xử lý Caching Redis & Tạo Quiz
│       ├── telegram.py     # Gửi tin nhắn và phản hồi Telegram
│       └── voice.py        # Xử lý Text-to-Speech & Chunking âm thanh
├── render.yaml             # Cấu hình triển khai hạ tầng trên Render
├── requirements.txt        # Các thư viện phụ thuộc Python
└── README.md               # Tài liệu dự án
```

---
**Made with ❤️ for Productivity.**