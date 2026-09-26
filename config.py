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

# Đuôi file dùng để chọn CÁCH HIỂN THỊ trong thư viện (ảnh xem trực tiếp,
# video có khung phát, còn lại hiện dạng thẻ file + link mở/tải xuống) —
# KHÔNG dùng để chặn tải lên.
IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp", "bmp"}
VIDEO_EXT = {"mp4", "mov", "webm", "avi", "mkv", "m4v"}

# Mục "Hình ảnh" cho tải lên MỌI loại file (ảnh/video/docx/pdf/xlsx...),
# CHỈ chặn nhóm đuôi mà trình duyệt có thể CHẠY ngay khi mở trực tiếp link
# (HTML/SVG có thể chứa script, hoặc file thực thi) — tránh rủi ro chạy mã
# trên chính domain của app. Cần mở thêm/bớt đuôi thì sửa trực tiếp set này.
BLOCKED_UPLOAD_EXT = {
    "html", "htm", "svg", "js", "mjs", "php", "phtml",
    "exe", "sh", "bat", "cmd", "py", "jar", "msi",
}

# 16MB là quá nhỏ cho video — nâng lên 200MB. Nếu VPS ít dung lượng đĩa,
# hạ số này lại cho phù hợp.
MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB

# Danh sách "Loại ảnh" hiển thị trong dropdown khi tải file lên — cần thêm
# loại nào thì thêm thẳng vào list này (thứ tự ở đây = thứ tự hiện trong
# dropdown, mục đầu tiên là mặc định được chọn sẵn).
IMAGE_TYPES = [
    "Ảnh thẻ màu",
    "Ảnh trên gạch",
    "Ảnh máy đo màu",
    "Khác",
]