"""XÓA SẠCH toàn bộ dữ liệu hiện có trong database (KHÔNG seed lại gì cả).

CẢNH BÁO: xóa VĨNH VIỄN toàn bộ dữ liệu hiện tại — màu, phiên bản, pigment,
tài khoản, ảnh, nhật ký hoạt động... KHÔNG THỂ HOÀN TÁC. Chỉ xóa DỮ LIỆU,
KHÔNG đụng vào cấu trúc bảng/migration (Flask-Migrate không cần chạy lại).

Sau khi chạy xong, database sẽ HOÀN TOÀN RỖNG — không có tài khoản nào để
đăng nhập. Muốn có dữ liệu mẫu lại thì tự chạy thêm `python seed.py`.

Nếu trong DB đang có tài khoản/màu THẬT (không phải chỉ dữ liệu seed cũ),
sao lưu trước khi chạy (vd: pg_dump).

Chạy:
    python reset_db.py
"""
from models import connect, PGConnection

# Liệt kê đủ cả 9 bảng — TRUNCATE ... CASCADE tự xử lý đúng thứ tự khóa
# ngoại nên không cần quan tâm bảng nào phụ thuộc bảng nào.
ALL_TABLES = [
    "users", "pigments", "colors", "color_pigments",
    "color_versions", "color_version_pigments", "color_images",
    "user_permissions", "activity_logs",
]


def main():
    answer = input(
        "XÓA VĨNH VIỄN toàn bộ dữ liệu hiện tại trong database — không thể "
        "hoàn tác, và sẽ KHÔNG seed lại gì cả (database sẽ rỗng hoàn toàn).\n"
        "Gõ đúng chữ XOA rồi Enter để xác nhận, hoặc Enter trống để hủy: "
    ).strip()
    if answer.upper() != "XOA":
        print("Đã hủy — không có gì bị xóa.")
        return

    raw_conn = connect()
    conn = PGConnection(raw_conn)
    conn.execute(f"TRUNCATE TABLE {', '.join(ALL_TABLES)} RESTART IDENTITY CASCADE")
    conn.commit()
    conn.close()
    print("Đã xóa sạch toàn bộ dữ liệu (giữ nguyên cấu trúc bảng). "
          "Database hiện đang rỗng — chạy 'python seed.py' nếu muốn có dữ liệu mẫu lại.")


if __name__ == "__main__":
    main()