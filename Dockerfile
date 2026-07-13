FROM python:3.12-slim

# Cài đặt git và build-essential nếu cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy requirements trước để tận dụng cache Docker
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy toàn bộ code vào container
COPY . .

# Hugging Face Spaces yêu cầu chạy cổng 7860
EXPOSE 7860

# Command khởi động FastAPI app
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
