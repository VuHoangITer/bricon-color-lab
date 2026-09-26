"""Khai báo schema bằng SQLAlchemy — CHỈ để Flask-Migrate/Alembic soi và
sinh migration tự động (flask db migrate / flask db upgrade).

QUAN TRỌNG: đây KHÔNG phải tầng truy vấn của app. Toàn bộ code đọc/ghi dữ
liệu thực tế vẫn nằm ở models/user.py, models/color.py, v.v. — dùng SQL
thô qua get_db() (models/__init__.py) như trước giờ, KHÔNG đổi gì.
File này chỉ mô tả cấu trúc bảng để Alembic biết đường tạo/so sánh/sinh
migration khi bạn đổi schema (thêm bảng, thêm cột...).

Khi cần đổi schema:
  1. Sửa/thêm class bên dưới cho đúng ý muốn.
  2. flask db migrate -m "mô tả ngắn gọn"   (sinh file migration trong migrations/versions/)
  3. Mở file vừa sinh ra, đọc lại cho chắc (Alembic đôi khi sinh thừa/thiếu
     vài dòng, đặc biệt với cột SERIAL/sequence).
  4. flask db upgrade                        (áp dụng vào DB thật)
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import REAL

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.Text)
    role = db.Column(db.Text, nullable=False, server_default="san_xuat")
    is_active = db.Column(db.Integer, nullable=False, server_default="1")
    deactivated_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())


class UserPermission(db.Model):
    __tablename__ = "user_permissions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission = db.Column(db.Text, nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "permission"),)


class Pigment(db.Model):
    __tablename__ = "pigments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    display_order = db.Column(db.Integer, server_default="0")


class Color(db.Model):
    __tablename__ = "colors"
    id = db.Column(db.Integer, primary_key=True)
    ma_mau = db.Column(db.Text, unique=True, nullable=False)
    ten_mau = db.Column(db.Text)
    ghi_chu = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    qr_code_path = db.Column(db.Text)
    hex_color = db.Column(db.Text)
    # Lab đo THẬT từ máy đo màu (D65/10° hay theo máy đang dùng) — ưu tiên
    # hơn hex_color khi so màu (xem models/color.py::get_lab), vì HEX 8-bit
    # làm mất chi tiết so với số Lab máy đo ra, nhất là vùng màu tối. Cả 3
    # cột cùng NULL nếu màu chưa được đo bằng máy (khi đó so màu tự suy Lab
    # từ hex_color như cách cũ).
    lab_l = db.Column(REAL)
    lab_a = db.Column(REAL)
    lab_b = db.Column(REAL)
    trang_thai_duyet = db.Column(db.Text, nullable=False, server_default="CHO_DUYET")
    duyet_boi = db.Column(db.Integer, db.ForeignKey("users.id"))
    duyet_luc = db.Column(db.DateTime)
    ly_do_tu_choi = db.Column(db.Text)


class ColorPigment(db.Model):
    __tablename__ = "color_pigments"
    id = db.Column(db.Integer, primary_key=True)
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id", ondelete="CASCADE"), nullable=False)
    pigment_id = db.Column(db.Integer, db.ForeignKey("pigments.id"), nullable=False)
    ty_le = db.Column(REAL, nullable=False, server_default="0")
    __table_args__ = (db.UniqueConstraint("color_id", "pigment_id"),)


class ColorVersion(db.Model):
    __tablename__ = "color_versions"
    id = db.Column(db.Integer, primary_key=True)
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id", ondelete="CASCADE"), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    ghi_chu = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    trang_thai_duyet = db.Column(db.Text, nullable=False, server_default="CHO_DUYET")
    duyet_boi = db.Column(db.Integer, db.ForeignKey("users.id"))
    duyet_luc = db.Column(db.DateTime)
    ly_do_tu_choi = db.Column(db.Text)
    is_active = db.Column(db.Integer, nullable=False, server_default="0")
    __table_args__ = (db.UniqueConstraint("color_id", "version_number"),)


class ColorVersionPigment(db.Model):
    __tablename__ = "color_version_pigments"
    id = db.Column(db.Integer, primary_key=True)
    version_id = db.Column(db.Integer, db.ForeignKey("color_versions.id", ondelete="CASCADE"), nullable=False)
    pigment_id = db.Column(db.Integer, db.ForeignKey("pigments.id"), nullable=False)
    ty_le = db.Column(REAL, nullable=False, server_default="0")
    __table_args__ = (db.UniqueConstraint("version_id", "pigment_id"),)


class ColorImage(db.Model):
    __tablename__ = "color_images"
    id = db.Column(db.Integer, primary_key=True)
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id", ondelete="CASCADE"), nullable=False)
    file_path = db.Column(db.Text, nullable=False)
    loai_anh = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    uploaded_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    ghi_chu = db.Column(db.Text)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.Text, nullable=False)
    target_type = db.Column(db.Text)
    target_id = db.Column(db.Integer)
    detail = db.Column(db.Text)
    hidden = db.Column(db.Integer, nullable=False, server_default="0")
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())


class WeighingRecord(db.Model):
    """Bản ghi CỐ ĐỊNH (snapshot) của 1 lần tạo phiếu cân — dùng để sinh
    link public qua QR. Toàn bộ thông tin hiển thị (mã màu, tên màu, người
    tạo, ngày) được CHỤP LẠI thành text ngay lúc tạo, không tham chiếu sống
    tới colors/users — nên dù công thức/tên màu đổi, hay tài khoản người
    tạo bị xóa, thông tin public vẫn giữ nguyên y hệt lúc cân."""
    __tablename__ = "weighing_records"
    id = db.Column(db.Integer, primary_key=True)
    public_token = db.Column(db.Text, unique=True, nullable=False)
    color_id = db.Column(db.Integer, db.ForeignKey("colors.id", ondelete="SET NULL"))
    ma_mau = db.Column(db.Text, nullable=False)
    ten_mau = db.Column(db.Text)
    tong_thanh_pham_g = db.Column(REAL, nullable=False)
    ty_le_pigment = db.Column(REAL, nullable=False)
    nguoi_tao = db.Column(db.Text, nullable=False)
    ngay_tao = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())