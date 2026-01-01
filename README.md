# 🎓 UEH Notion Assistant

**UEH Notion Assistant** là một trợ lý ảo cá nhân hóa, giúp tự động hóa việc quản lý học tập và công việc từ Notion sang Telegram. Hệ thống sử dụng AI (Google Gemini) để phân tích nhiệm vụ, lên kế hoạch trong ngày và tạo bộ câu hỏi ôn tập thông minh.

---

## 🚀 Tính Năng Chính

### 1. 📅 Daily Report (Báo Cáo Ngày)
-   **Tự động quét Notion**: Lấy danh sách task cần làm trong ngày.
-   **Phân tích AI**: Sử dụng Gemini để lập kế hoạch theo ma trận Eisenhower và "Eat the Frog".
-   **Gửi Telegram**: Gửi bản tin text và **Voice Note** (kịch bản AI + giọng đọc AI) vào mỗi sáng (7:15 AM).

### 2. 🧠 Study Assistant (Trợ Lý Ôn Tập)
-   **Active Recall**: Tìm các bài ghi chép có trạng thái `🔴 Cần xem lại`.
-   **Deep Dive**: Quét sâu nội dung bài học (bao gồm text, headings, list...).
-   **AI Quiz**: Tạo bộ câu hỏi trắc nghiệm/tự luận ngắn (có che đáp án spoiler) để ôn tập ngay trên Telegram.
-   **Chế độ yên lặng**: Gửi câu hỏi dồn dập nhưng không spam thông báo.

---

## 🏗️ Kiến Trúc Hệ Thống

Project được thiết kế theo mô hình **Service-Oriented** để dễ dàng mở rộng:

```text
UEH-Notion/
├── src/
│   ├── config/       # Quản lý biến môi trường (.env)
│   ├── services/     # Tương tác với API bên ngoài
│   │   ├── motion.py    # Notion API
│   │   ├── ai.py        # Google Gemini AI
│   │   ├── telegram.py  # Telegram Bot API
│   │   └── voice.py     # Edge TTS (Voice Generation)
│   ├── jobs/         # Logic nghiệp vụ chính
│   │   ├── daily_report.py
│   │   └── study_assistant.py
│   └── main.py       # Điểm khởi chạy (CLI Entry Point)
```

---

## 🛠️ Cài Đặt và Cấu Hình

### 1. Yêu cầu hệ thống
-   Python 3.12+
-   Tài khoản Notion (Integration Token)
-   Tài khoản Google AI Studio (Gemini API Key)
-   Telegram Bot (Token & Chat ID)

### 2. Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` tại thư mục gốc và điền các thông tin sau:

```ini
# Notion
NOTION_TOKEN=secret_xxxxxxxx
NOTION_DATABASE_ID=xxxxxxxx  # DB Task
NOTION_DB_GHI_CHEP_ID=xxxxxxxx # DB Ghi chép bài học

# AI
GEMINI_API_KEY=AIzaSy...

# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789
```

---

## 🎮 Hướng Dẫn Sử Dụng

Project sử dụng một entry point duy nhất là `src/main.py`.

### Chạy Daily Report
```bash
python src/main.py run daily-report
```

### Chạy Study Assistant
```bash
python src/main.py run study-assistant
```

---

## 🤖 Tự Động Hóa (GitHub Actions)

Project đã tích hợp sẵn GitHub Actions để chạy định kỳ:

| Workflow | Lịch chạy (Giờ VN) | Mô tả |
| :--- | :--- | :--- |
| **Daily Report** | 07:15 | Báo cáo công việc đầu ngày |
| **Study Assistant** | 08:00, 12:00, 16:00, 20:00 | Nhắc nhở ôn bài rải rác trong ngày |

---

## 📝 Nhật Ký Thay Đổi (Changelog)

-   **Refactor**: Chuyển đổi sang kiến trúc Service-Oriented (Modular).
-   **Study Assistant**: Thêm tính năng split tin nhắn Telegram và Silent Mode.
-   **AI**: Nâng cấp lên model `gemini-2.0-flash-exp` cho khả năng suy luận tốt hơn.

---

**Made with ❤️ by Khôi Trần for Productivity.**
