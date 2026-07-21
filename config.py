import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

# --- Kết nối PostgreSQL — đặt các giá trị thật trong file .env (xem
# .env.example), KHÔNG hard-code mật khẩu thật vào đây. ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "bricon_color_lab")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
# Múi giờ áp dụng cho MỌI kết nối DB — để các cột TIMESTAMP (created_at,
# duyet_luc, deactivated_at...) lưu đúng giờ Việt Nam, giữ hành vi giống
# hệt datetime('now','localtime') hồi còn SQLite mà không cần sửa template.
DB_TIMEZONE = os.getenv("DB_TIMEZONE", "Asia/Ho_Chi_Minh")

BASE_URL = os.getenv("BASE_URL", "http://localhost:5000").rstrip("/")
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
PORT = int(os.getenv("PORT", "5000"))

UPLOAD_ROOT = BASE_DIR / "static" / "uploads"
QR_FOLDER = UPLOAD_ROOT / "qr"
IMAGE_FOLDER = UPLOAD_ROOT / "images"
PDF_FOLDER = UPLOAD_ROOT / "pdf"
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

IMAGE_TYPES = [
    "Ảnh màu mục tiêu",
    "Ảnh pigment đã cân",
    "Ảnh mẫu khi ướt",
    "Ảnh mẫu sau 24h",
    "Ảnh trên gạch",
    "Ảnh máy đo màu",
    "Khác",
]