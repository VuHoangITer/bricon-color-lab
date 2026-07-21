from models import get_db


def all_ordered():
    return get_db().execute(
        "SELECT * FROM pigments ORDER BY display_order, id"
    ).fetchall()


def all_with_usage():
    """Kèm số PHIÊN BẢN màu đang dùng pigment này (ty_le > 0). Tính trên
    color_version_pigments — bảng công thức THẬT của hệ thống phiên bản —
    KHÔNG phải color_pigments (bảng từ thời chưa có phiên bản, giờ không
    còn được ghi dữ liệu nữa; dùng bảng đó sẽ luôn ra 0, dù pigment đang
    được dùng thật trong công thức)."""
    return get_db().execute(
        """SELECT p.*, COUNT(CASE WHEN cvp.ty_le > 0 THEN 1 END) AS so_mau_dung
           FROM pigments p
           LEFT JOIN color_version_pigments cvp ON cvp.pigment_id = p.id
           GROUP BY p.id ORDER BY p.display_order, p.id"""
    ).fetchall()


def get(pigment_id):
    return get_db().execute("SELECT * FROM pigments WHERE id = %s", (pigment_id,)).fetchone()


def usage_count(pigment_id):
    return get_db().execute(
        "SELECT COUNT(*) AS n FROM color_version_pigments WHERE pigment_id = %s AND ty_le > 0",
        (pigment_id,),
    ).fetchone()["n"]


def create(name):
    db = get_db()
    order = db.execute(
        "SELECT COALESCE(MAX(display_order),0)+1 AS next_order FROM pigments"
    ).fetchone()["next_order"]
    cur = db.execute(
        "INSERT INTO pigments (name, display_order) VALUES (%s,%s) RETURNING id",
        (name.strip(), order),
    )
    pigment_id = cur.fetchone()["id"]
    db.commit()
    return pigment_id


def rename(pigment_id, name):
    db = get_db()
    db.execute("UPDATE pigments SET name = %s WHERE id = %s", (name.strip(), pigment_id))
    db.commit()


def delete(pigment_id):
    """Chỉ xóa được khi không có phiên bản màu nào đang dùng thật (ty_le > 0).
    Dọn kèm các dòng ty_le = 0 (nếu có) ở color_version_pigments, và cả
    color_pigments (bảng cũ — phòng khi còn sót dữ liệu từ trước)."""
    if usage_count(pigment_id) > 0:
        raise ValueError("Pigment đang được dùng trong công thức màu — không thể xóa.")
    db = get_db()
    db.execute("DELETE FROM color_version_pigments WHERE pigment_id = %s", (pigment_id,))
    db.execute("DELETE FROM color_pigments WHERE pigment_id = %s", (pigment_id,))
    db.execute("DELETE FROM pigments WHERE id = %s", (pigment_id,))
    db.commit()