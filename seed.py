"""Seed dữ liệu ban đầu (pigment, 30 màu mẫu, 4 tài khoản demo).

Chạy SAU KHI đã tạo bảng bằng Flask-Migrate:
    flask db upgrade
    python seed.py
"""
from werkzeug.security import generate_password_hash
import config
from models import PGConnection, connect

PIGMENTS = [
    "TITAN - TRẮNG", "ĐEN", "XANH DƯƠNG", "XANH LỤC",
    "VÀNG", "ĐỎ ĐẬM", "MTL 1984 LỤC LAM", "MTL 2221 CAMAY RÊU",
]

# (ma_mau, ten_mau, hex_color, [8 tỷ lệ theo thứ tự PIGMENTS], ghi_chu)
# Đối chiếu đúng theo sheet "BẢNG MÀU V4" trong FILE_CÂN_MÀU_MỞ_RỘNG.xlsx —
# cả 30 màu đều ĐẠT (tổng = 100%). Ghi chú ở màu 3/4/7/8 là chú thích lịch sử
# giữ nguyên từ file gốc, không phải lỗi.
COLORS = [
    ("1",  "Trắng sứ",         "#F7F6F2", [1, 0, 0, 0, 0, 0, 0, 0], ""),
    ("2",  "Vàng kem sữa",     "#FCEDBA", [0.96, 0, 0, 0, 0.04, 0, 0, 0], ""),
    ("3",  "Kem ngà",          "#F9E7BD", [0.9, 0, 0, 0, 0.095, 0.005, 0, 0], ""),
    ("4",  "Hồng sứ",          "#FBE7E4", [0.94, 0, 0, 0, 0, 0.06, 0, 0], ""),
    ("5",  "Xám xi măng",      "#999B9F", [0.85, 0.15, 0, 0, 0, 0, 0, 0], ""),
    ("6",  "Vàng kem",         "#FCD999", [0.42, 0, 0, 0, 0.58, 0, 0, 0], ""),
    ("7",  "Xám đậm",          "#676E78", [0.75, 0.25, 0, 0, 0, 0, 0, 0], ""),
    ("8",  "Hồng đất",         "#D17A5F", [0.52, 0.14, 0.14, 0, 0, 0.2, 0, 0], ""),
    ("9",  "Nâu đỏ",           "#85361F", [0.52, 0.08, 0, 0, 0.06, 0.34, 0, 0], ""),
    ("10", "Nâu gỗ",           "#AD5A1C", [0.67, 0.03, 0, 0, 0.18, 0.12, 0, 0], ""),
    ("11", "Xanh biển nhạt",   "#D8E6F2", [0.6, 0, 0.25, 0.15, 0, 0, 0, 0], ""),
    ("12", "Xanh ngọc nhạt",   "#DAE5BA", [0.74, 0.01, 0, 0.14, 0.11, 0, 0, 0], ""),
    ("13", "Xám rêu nhạt",     "#DBD6B8", [0.72, 0.03, 0, 0.14, 0.11, 0, 0, 0], ""),
    ("14", "Xanh biển sáng",   "#58CAF9", [0, 0, 1, 0, 0, 0, 0, 0], ""),
    ("15", "Hồng be",          "#F8C5AD", [0.6, 0.04, 0, 0, 0.18, 0.18, 0, 0], ""),
    ("16", "Xanh băng",        "#C5EDF4", [0, 0, 0, 0, 0, 0, 1, 0], ""),
    ("17", "Xám bạc",          "#CDCBCA", [0.945, 0.055, 0, 0, 0, 0, 0, 0], ""),
    ("18", "Xanh da trời",     "#B8D2EA", [0.72, 0.03, 0.05, 0.2, 0, 0, 0, 0], ""),
    ("19", "Nâu hồng xám",     "#C48B7D", [0.73, 0.05, 0, 0, 0.05, 0.17, 0, 0], ""),
    ("20", "Cam san hô",       "#FC8A63", [0.62, 0.04, 0, 0, 0.18, 0.16, 0, 0], ""),
    ("21", "Xanh mint nhạt",   "#D1F0E5", [0.32, 0.02, 0.38, 0.28, 0, 0, 0, 0], ""),
    ("22", "Kem sữa",          "#FBE1BC", [0.68, 0, 0, 0, 0.32, 0, 0, 0], ""),
    ("23", "Nâu gỗ đậm",       "#865325", [0.56, 0.06, 0, 0, 0.2, 0.18, 0, 0], ""),
    ("24", "Xám trắng",        "#EBE7E2", [0.98, 0.02, 0, 0, 0, 0, 0, 0], ""),
    ("25", "Đỏ gạch nung",     "#CC2B07", [0, 0.18, 0, 0, 0.04, 0.78, 0, 0], ""),
    ("26", "Xanh ngọc đậm",    "#26746E", [0, 0, 0, 1, 0, 0, 0, 0], ""),
    ("27", "Vàng",             "#FBD476", [0, 0, 0, 0, 1, 0, 0, 0], ""),
    ("28", "Cam Đào",          "#F99675", [0.2, 0, 0, 0, 0.32, 0.48, 0, 0], ""),
    ("29", "Đen kim cương",    "#111110", [0, 1, 0, 0, 0, 0, 0, 0], ""),
    ("30", "Xanh cổ vịt nhạt", "#62B7B7", [0, 0, 0, 0, 0, 0, 0, 1], ""),
]

# (username, password, full_name, role) — tài khoản demo cho từng vai trò.
# ĐỔI MẬT KHẨU sau khi dùng thật, đặc biệt là admin.
DEFAULT_USERS = [
    ("admin", "admin123", "Quản trị viên", "admin"),
    ("quanly", "quanly123", "Quản lý Lab", "quan_ly"),
    ("sanxuat", "sanxuat123", "Nhân viên sản xuất", "san_xuat"),
    ("khachhang", "khachhang123", "Khách hàng demo", "khach_hang"),
]


def main():
    raw_conn = connect()
    conn = PGConnection(raw_conn)

    try:
        already_seeded = conn.execute("SELECT COUNT(*) AS n FROM colors").fetchone()["n"] > 0
    except Exception:
        print("Chưa có bảng nào trong database — chạy 'flask db upgrade' trước rồi mới chạy lại seed.py.")
        return
    if already_seeded:
        print("Database đã có dữ liệu — bỏ qua seed. Tạo database Postgres mới nếu muốn seed lại từ đầu.")
        return

    admin_id = None
    for username, password, full_name, role in DEFAULT_USERS:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s) RETURNING id",
            (username, generate_password_hash(password), full_name, role))
        uid = cur.fetchone()["id"]
        if role == "admin":
            admin_id = uid

    pigment_ids = []
    for i, name in enumerate(PIGMENTS, 1):
        cur = conn.execute(
            "INSERT INTO pigments (name, display_order) VALUES (%s,%s) RETURNING id", (name, i))
        pigment_ids.append(cur.fetchone()["id"])

    for ma_mau, ten_mau, hex_color, ratios, ghi_chu in COLORS:
        cur = conn.execute(
            "INSERT INTO colors (ma_mau, ten_mau, ghi_chu, created_by, hex_color) VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (ma_mau, ten_mau, ghi_chu, admin_id, hex_color))
        color_id = cur.fetchone()["id"]
        cur = conn.execute(
            """INSERT INTO color_versions
               (color_id, version_number, created_by, trang_thai_duyet, duyet_boi, duyet_luc, is_active)
               VALUES (%s,1,%s,%s,%s,CURRENT_TIMESTAMP,1) RETURNING id""",
            (color_id, admin_id, "DA_DUYET", admin_id))
        version_id = cur.fetchone()["id"]
        for pid, ty_le in zip(pigment_ids, ratios):
            conn.execute(
                "INSERT INTO color_version_pigments (version_id, pigment_id, ty_le) VALUES (%s,%s,%s)",
                (version_id, pid, ty_le))

    conn.commit()
    conn.close()
    print(f"Seed xong: {len(PIGMENTS)} pigment, {len(COLORS)} màu — mỗi màu có sẵn Phiên bản 1 (ĐÃ DUYỆT, đang dùng).")
    print("Tài khoản demo (đổi mật khẩu sau khi dùng thật):")
    for username, password, full_name, role in DEFAULT_USERS:
        print(f"  - {username} / {password}  ({role})")
    print("QR sẽ tự sinh khi tạo màu mới; 30 màu seed chưa có QR — mở chi tiết màu sẽ thấy nút tạo QR.")


if __name__ == "__main__":
    main()