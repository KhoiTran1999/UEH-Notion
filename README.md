# 🎓 UEH Notion Assistant

**UEH Notion Assistant** là một trợ lý ảo cá nhân hóa, giúp tự động hóa và tối ưu quy trình học tập, quản lý công việc từ Notion kết hợp với sức mạnh của AI.

Hệ thống tự động phân tích nhiệm vụ trong ngày, nhắc nhở ôn tập theo phương pháp **Spaced Repetition** (lặp lại ngắt quãng) và gửi thông báo trực tiếp qua Telegram.

---

## 🚀 Tính Năng Chính

### 1. 📅 Daily Report (Báo Cáo Đầu Ngày)
- **Tự động quét Notion**: Lấy danh sách task cần làm trong ngày.
- **Phân tích AI**: Sử dụng Gemini để lập kế hoạch, sắp xếp công việc theo ma trận Eisenhower.
- **Voice Briefing**: Gửi bản tin âm thanh (Voice Note) tóm tắt lịch trình để nghe vào buổi sáng.
- **Lịch chạy**: 07:15 AM mỗi ngày.

### 2. 🧠 Study Assistant (Trợ Lý Ôn Tập)
- **Active Recall**: Tìm các bài ghi chép cũ cần ôn lại (dựa trên thuật toán Spaced Repetition).
- **AI Quiz**: Tự động tạo câu hỏi trắc nghiệm/tự luận từ nội dung bài học.
- **Tương tác Telegram**: Gửi câu hỏi và đáp án (dạng spoiler) để bạn tự kiểm tra kiến thức.
- **Silent Mode**: Gửi câu hỏi dồn dập nhưng không làm phiền (chỉ thông báo tin đầu tiên).
- **Lịch chạy**: 08:00, 12:00, 16:00, 20:00.

---

## 🛠️ Yêu Cầu Hệ Thống

- **Python**: 3.12 trở lên
- **Tài khoản Notion**: Đã tạo Integration và share database.
- **Google AI Studio**: API Key cho model Gemini.
- **Telegram Bot**: Token bot và Chat ID của người nhận.

---

## ⚙️ Cài Đặt

1. **Clone project:**
   ```bash
   git clone <repo_url>
   cd UEH-Notion
   ```

2. **Cài đặt thư viện:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Cấu hình biến môi trường:**
   Tạo file `.env` tại thư mục gốc và điền thông tin tương ứng (xem file `.env.example`):
   ```ini
   NOTION_TOKEN=secret_...
   NOTION_DB_TASK=...
   NOTION_DB_GHI_CHEP_ID=...
   GEMINI_API_KEY=AIzaSy...
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```

---

## 🎮 Hướng Dẫn Sử Dụng (Command Line)

Project sử dụng `src/main.py` làm điểm truy cập chính. Bạn có thể chạy thủ công các tác vụ thông qua dòng lệnh.

### 1. Chạy Báo Cáo Ngày (Daily Report)
Tác vụ này sẽ quét Notion task và gửi báo cáo + voice note.
```bash
python src/main.py run daily-report
```

### 2. Chạy Trợ Lý Ôn Tập (Study Assistant)
Tác vụ này sẽ chọn bài học cần ôn và gửi câu hỏi trắc nghiệm.
```bash
python src/main.py run study-assistant
```

---

## 🤖 Tự Động Hóa (GitHub Actions & Cloudflare Worker)

Project được cấu hình với **GitHub Actions** để chạy trên cloud. Kết hợp với **Cloudflare Worker** để nhận lệnh trực tiếp từ Telegram Bot thông qua Webhook.

### Lệnh Telegram hỗ trợ
- `/start` hoặc `/help`: Hiển thị menu chức năng dưới dạng nút bấm (Inline Keyboard).
- `/taskreport`: Chạy báo cáo ngày ngay lập tức.
- `/study`: Gọi danh sách bài cần ôn (tối đa 5 bài cũ nhất). Bạn bấm chọn bài nào, bot sẽ soạn trắc nghiệm bài đó.

### Cài đặt Cloudflare Worker (Telegram Webhook)
1. Tạo một Worker trên Cloudflare.
2. Copy toàn bộ code trong file `cloudflare_worker.js` dán vào.
3. Thiết lập các Environment Variables sau trên Cloudflare:
   - `TG_BOT_TOKEN`: Token của bot Telegram.
   - `GITHUB_TOKEN`: GitHub Personal Access Token (PAT) có quyền `repo` và `workflow`.
   - `GITHUB_OWNER`: Tên username GitHub của bạn.
   - `GITHUB_REPO`: Tên repository (vd: `UEH-Notion`).
4. Set Webhook cho Telegram Bot trỏ về URL của Cloudflare Worker:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TG_BOT_TOKEN>/setWebhook" -d "url=<CLOUDFLARE_WORKER_URL>"
   ```

## ⏰ Setup Cron Job (Tự động chạy theo giờ)

Để chạy workflow theo lịch tùy chỉnh (hoặc miễn phí trigger không giới hạn), bạn có thể dùng **cron-job.org**.

### 1. Tạo GitHub Personal Access Token (PAT)
1. Vào **GitHub Settings** -> **Developer settings** -> **Personal access tokens** -> **Tokens (classic)**.
2. Chọn **Generate new token (classic)**.
3. Chọn scope `workflow` (để có quyền trigger workflow).
4. Lưu lại token này (ví dụ: `ghp_...`).

### 2. Cấu hình trên cron-job.org
1. Đăng ký/Đăng nhập tại [cron-job.org](https://cron-job.org/).
2. Chọn **Create Cronjob**.
3. Điền thông tin:
   - **URL**: `https://api.github.com/repos/<username>/<repo>/actions/workflows/study_assistant.yml/dispatches`
     - Thay `<username>`: Tên tài khoản GitHub của bạn.
     - Thay `<repo>`: Tên repository (ví dụ: `UEH-Notion`).
   - **Execution schedule**: Chọn lịch chạy mong muốn (ví dụ: mỗi 4 tiếng).
4. Trong phần **Advanced**:
   - **HTTP Method**: `POST`
   - **Headers**:
     ```text
     Accept: application/vnd.github.v3+json
     Authorization: Bearer <YOUR_GITHUB_PAT>
     User-Agent: cron-job
     ```
   - **Body (JSON)**:
     ```json
     {"ref": "main"}
     ```
5. Bấm **Create Cronjob**.

---

## 📂 Cấu Trúc Project

```text
UEH-Notion/
├── src/
│   ├── jobs/               # Chứa logic của từng tác vụ (Daily Report, Study Assistant)
│   ├── services/           # Các module kết nối API (Notion, Telegram, AI, Voice)
│   ├── config/             # Cấu hình hệ thống
│   └── main.py             # Entry point của chương trình
├── .github/workflows/      # Cấu hình tự động hóa GitHub Actions
├── .env.example            # Mẫu file cấu hình
├── requirements.txt        # Danh sách thư viện
└── README.md               # Tài liệu hướng dẫn
```

---
**Made with ❤️ for Productivity.**
