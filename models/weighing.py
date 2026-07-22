import secrets
from models import get_db


def create(color_id, ma_mau, ten_mau, tong_thanh_pham_g, ty_le_pigment,
           nguoi_tao, ngay_tao, created_by):
    """Lưu 1 bản ghi CỐ ĐỊNH (snapshot) của phiếu cân — dùng để sinh link
    công khai qua QR. token là chuỗi ngẫu nhiên không đoán được (128 bit),
    dùng làm định danh trong link public thay vì id tuần tự (tránh dò link
    theo số thứ tự)."""
    token = secrets.token_urlsafe(16)
    db = get_db()
    db.execute(
        """INSERT INTO weighing_records
           (public_token, color_id, ma_mau, ten_mau, tong_thanh_pham_g,
            ty_le_pigment, nguoi_tao, ngay_tao, created_by)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (token, color_id, ma_mau, ten_mau, tong_thanh_pham_g, ty_le_pigment,
         nguoi_tao, ngay_tao, created_by),
    )
    db.commit()
    return token


def get_by_token(token):
    return get_db().execute(
        "SELECT * FROM weighing_records WHERE public_token = %s", (token,)
    ).fetchone()