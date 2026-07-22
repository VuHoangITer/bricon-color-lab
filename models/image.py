from models import get_db


def create(color_id, file_path, loai_anh, user_id, ghi_chu=""):
    db = get_db()
    cur = db.execute(
        """INSERT INTO color_images (color_id, file_path, loai_anh, uploaded_by, ghi_chu)
           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
        (color_id, file_path, loai_anh, user_id, ghi_chu),
    )
    image_id = cur.fetchone()["id"]
    db.commit()
    return image_id


def list_for_color(color_id):
    return get_db().execute(
        """SELECT i.*, u.username FROM color_images i
           LEFT JOIN users u ON u.id = i.uploaded_by
           WHERE i.color_id = %s ORDER BY i.id DESC""",
        (color_id,),
    ).fetchall()


def get(image_id):
    return get_db().execute("SELECT * FROM color_images WHERE id = %s", (image_id,)).fetchone()


def list_all(page=1, per_page=50, color_id=None, uploaded_by=None, loai_anh=None):
    """Toàn bộ ảnh trong hệ thống (mọi màu), mới nhất trước — dùng cho
    trang Thư viện ảnh (admin). Kèm mã màu/tên màu và người tải lên."""
    page = max(1, page)
    q = """SELECT i.*, c.ma_mau, c.ten_mau, u.username, u.full_name
           FROM color_images i
           JOIN colors c ON c.id = i.color_id
           LEFT JOIN users u ON u.id = i.uploaded_by
           WHERE 1=1"""
    params = []
    if color_id:
        q += " AND i.color_id = %s"
        params.append(color_id)
    if uploaded_by:
        q += " AND i.uploaded_by = %s"
        params.append(uploaded_by)
    if loai_anh:
        q += " AND i.loai_anh = %s"
        params.append(loai_anh)
    q += " ORDER BY i.id DESC LIMIT %s OFFSET %s"
    params += [per_page, (page - 1) * per_page]
    return get_db().execute(q, params).fetchall()


def count_all(color_id=None, uploaded_by=None, loai_anh=None):
    q = "SELECT COUNT(*) AS n FROM color_images i WHERE 1=1"
    params = []
    if color_id:
        q += " AND i.color_id = %s"
        params.append(color_id)
    if uploaded_by:
        q += " AND i.uploaded_by = %s"
        params.append(uploaded_by)
    if loai_anh:
        q += " AND i.loai_anh = %s"
        params.append(loai_anh)
    return get_db().execute(q, params).fetchone()["n"]


def delete(image_id):
    db = get_db()
    db.execute("DELETE FROM color_images WHERE id = %s", (image_id,))
    db.commit()


def delete_by_path(file_path):
    """Xóa dòng color_images khớp đúng file_path (nếu có) — dùng khi xóa
    file trực tiếp qua trang quét đĩa, tránh còn sót DB row trỏ tới file đã
    mất (ảnh vỡ trên trang chi tiết màu). Không báo lỗi nếu không có dòng
    nào khớp — file có thể vốn đã là 'mồ côi' (chưa từng có trong DB)."""
    db = get_db()
    db.execute("DELETE FROM color_images WHERE file_path = %s", (file_path,))
    db.commit()