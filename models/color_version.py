from models import get_db
from models.color import TOLERANCE, status_of

DUYET_CHO = "CHO_DUYET"
DUYET_DA = "DA_DUYET"
DUYET_TU_CHOI = "TU_CHOI"

DUYET_LABELS = {
    DUYET_CHO: "CHỜ DUYỆT",
    DUYET_DA: "ĐÃ DUYỆT",
    DUYET_TU_CHOI: "TỪ CHỐI",
}


def validate_ratios(ratios):
    """ratios: dict {pigment_id: ty_le}. Trả về (ok, total, message)."""
    total = sum(ratios.values())
    if not any(v > 0 for v in ratios.values()):
        return False, total, "Chưa nhập tỷ lệ pigment nào."
    if abs(total - 1.0) >= TOLERANCE:
        return False, total, f"Tổng pigment = {total*100:.2f}%, phải đúng 100% mới được lưu."
    return True, total, ""


def _next_version_number(color_id):
    row = get_db().execute(
        "SELECT COALESCE(MAX(version_number),0) AS next_num FROM color_versions WHERE color_id=%s",
        (color_id,),
    ).fetchone()
    return (row["next_num"] or 0) + 1


def has_pending(color_id):
    """True nếu màu này đang có 1 phiên bản CHỜ DUYỆT — dùng để chặn tạo
    thêm phiên bản mới cho tới khi phiên bản đó được xử lý xong, tránh
    chồng chéo nhiều bản chờ duyệt cùng lúc cho cùng 1 màu."""
    return get_db().execute(
        "SELECT COUNT(*) AS n FROM color_versions WHERE color_id=%s AND trang_thai_duyet=%s",
        (color_id, DUYET_CHO),
    ).fetchone()["n"] > 0


def create_version(color_id, ratios, user_id, ghi_chu="", auto_approve=False,
                    skip_validation=False):
    """Tạo phiên bản MỚI cho màu (không đụng các phiên bản cũ).
    auto_approve=True (người tạo có quyền duyệt sẵn) -> ĐÃ DUYỆT và trở
    thành bản đang dùng ngay lập tức. Ngược lại -> CHỜ DUYỆT."""
    if not skip_validation:
        ok, _, msg = validate_ratios(ratios)
        if not ok:
            raise ValueError(msg)
    db = get_db()
    vnum = _next_version_number(color_id)
    if auto_approve:
        cur = db.execute(
            """INSERT INTO color_versions
               (color_id, version_number, ghi_chu, created_by, trang_thai_duyet,
                duyet_boi, duyet_luc, is_active)
               VALUES (%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP,1) RETURNING id""",
            (color_id, vnum, (ghi_chu or "").strip(), user_id, DUYET_DA, user_id),
        )
        version_id = cur.fetchone()["id"]
        db.execute(
            "UPDATE color_versions SET is_active=0 WHERE color_id=%s AND id<>%s",
            (color_id, version_id),
        )
    else:
        cur = db.execute(
            """INSERT INTO color_versions
               (color_id, version_number, ghi_chu, created_by, trang_thai_duyet)
               VALUES (%s,%s,%s,%s,%s) RETURNING id""",
            (color_id, vnum, (ghi_chu or "").strip(), user_id, DUYET_CHO),
        )
        version_id = cur.fetchone()["id"]
    for pid, ty_le in ratios.items():
        db.execute(
            "INSERT INTO color_version_pigments (version_id, pigment_id, ty_le) VALUES (%s,%s,%s)",
            (version_id, pid, ty_le),
        )
    db.commit()
    return version_id


def get(version_id):
    return get_db().execute("SELECT * FROM color_versions WHERE id=%s", (version_id,)).fetchone()


def update_ratios(version_id, ratios, ghi_chu=None, skip_validation=False, resubmit=False):
    """Sửa TRỰC TIẾP tỷ lệ của 1 phiên bản ĐÃ TỒN TẠI — không tạo bản mới,
    không đổi version_number. Dùng cho sửa lỗi nhỏ/chỉnh nhanh phiên bản
    hiện tại, khác với create_version() (luôn tạo hẳn 1 bản mới tách biệt).

    resubmit=True: dùng khi CHÍNH CHỦ sửa lại 1 phiên bản đã bị TỪ CHỐI —
    tự động chuyển trạng thái về CHỜ DUYỆT (gửi lại xin duyệt) và xóa lý do
    từ chối cũ. KHÔNG dùng khi Admin/Quản lý sửa (họ sửa áp dụng ngay, giữ
    nguyên trạng thái hiện tại, không cần qua lại vòng duyệt)."""
    if not skip_validation:
        ok, _, msg = validate_ratios(ratios)
        if not ok:
            raise ValueError(msg)
    db = get_db()
    if ghi_chu is not None:
        db.execute("UPDATE color_versions SET ghi_chu=%s WHERE id=%s", (ghi_chu.strip(), version_id))
    if resubmit:
        db.execute(
            """UPDATE color_versions SET trang_thai_duyet=%s, ly_do_tu_choi=NULL,
               duyet_boi=NULL, duyet_luc=NULL WHERE id=%s""",
            (DUYET_CHO, version_id),
        )
    db.execute("DELETE FROM color_version_pigments WHERE version_id=%s", (version_id,))
    for pid, ty_le in ratios.items():
        db.execute(
            "INSERT INTO color_version_pigments (version_id, pigment_id, ty_le) VALUES (%s,%s,%s)",
            (version_id, pid, ty_le),
        )
    db.commit()


def get_ratio_rows(version_id):
    return get_db().execute(
        """SELECT cvp.pigment_id, p.name, cvp.ty_le FROM color_version_pigments cvp
           JOIN pigments p ON p.id = cvp.pigment_id
           WHERE cvp.version_id=%s ORDER BY p.display_order, p.id""",
        (version_id,),
    ).fetchall()


def detail(version_id):
    v = get(version_id)
    if not v:
        return None
    rows = get_ratio_rows(version_id)
    total = sum(r["ty_le"] for r in rows)
    has_any = any(r["ty_le"] > 0 for r in rows)
    return {
        "version": v,
        "pigment_rows": rows,
        "active_rows": [r for r in rows if r["ty_le"] > 0],
        "total": total,
        "status": status_of(total, has_any),
    }


def list_for_color(color_id):
    """Toàn bộ phiên bản của 1 màu, mới nhất trước."""
    return get_db().execute(
        "SELECT * FROM color_versions WHERE color_id=%s ORDER BY version_number DESC",
        (color_id,),
    ).fetchall()


def get_active(color_id):
    """Phiên bản đang dùng của màu (nếu có) — luôn là bản ĐÃ DUYỆT."""
    return get_db().execute(
        "SELECT * FROM color_versions WHERE color_id=%s AND is_active=1", (color_id,)
    ).fetchone()


def list_pending():
    """Mọi phiên bản đang CHỜ DUYỆT, kèm mã màu/tên màu — cho trang duyệt chung."""
    return get_db().execute(
        """SELECT cv.*, c.ma_mau, c.ten_mau FROM color_versions cv
           JOIN colors c ON c.id = cv.color_id
           WHERE cv.trang_thai_duyet=%s ORDER BY cv.created_at DESC""",
        (DUYET_CHO,),
    ).fetchall()


def count_pending():
    return get_db().execute(
        "SELECT COUNT(*) AS n FROM color_versions WHERE trang_thai_duyet=%s", (DUYET_CHO,)
    ).fetchone()["n"]


def list_mine(user_id):
    """Phiên bản do user này tạo đang CHỜ DUYỆT/TỪ CHỐI, kèm mã màu/tên màu."""
    return get_db().execute(
        """SELECT cv.*, c.ma_mau, c.ten_mau FROM color_versions cv
           JOIN colors c ON c.id = cv.color_id
           WHERE cv.created_by=%s AND cv.trang_thai_duyet IN (%s,%s)
           ORDER BY cv.created_at DESC""",
        (user_id, DUYET_CHO, DUYET_TU_CHOI),
    ).fetchall()


def count_mine_pending_or_rejected(user_id):
    return get_db().execute(
        "SELECT COUNT(*) AS n FROM color_versions WHERE created_by=%s AND trang_thai_duyet IN (%s,%s)",
        (user_id, DUYET_CHO, DUYET_TU_CHOI),
    ).fetchone()["n"]


def approve(version_id, approver_id):
    """Duyệt phiên bản — tự động trở thành bản đang dùng, tắt active của
    các phiên bản khác cùng màu."""
    db = get_db()
    v = get(version_id)
    if not v:
        raise ValueError("Không tìm thấy phiên bản.")
    db.execute(
        """UPDATE color_versions SET trang_thai_duyet=%s, duyet_boi=%s,
           duyet_luc=CURRENT_TIMESTAMP, ly_do_tu_choi=NULL, is_active=1
           WHERE id=%s""",
        (DUYET_DA, approver_id, version_id),
    )
    db.execute(
        "UPDATE color_versions SET is_active=0 WHERE color_id=%s AND id<>%s",
        (v["color_id"], version_id),
    )
    db.commit()


def reject(version_id, approver_id, reason):
    db = get_db()
    db.execute(
        """UPDATE color_versions SET trang_thai_duyet=%s, duyet_boi=%s,
           duyet_luc=CURRENT_TIMESTAMP, ly_do_tu_choi=%s
           WHERE id=%s""",
        (DUYET_TU_CHOI, approver_id, reason, version_id),
    )
    db.commit()


def activate(version_id):
    """Đặt 1 phiên bản ĐÃ DUYỆT (kể cả bản cũ) làm bản đang dùng — dùng để
    'quay lại' V1/V2 sau khi lỡ lên V3 mà không ai ưng, không cần duyệt lại."""
    db = get_db()
    v = get(version_id)
    if not v:
        raise ValueError("Không tìm thấy phiên bản.")
    if v["trang_thai_duyet"] != DUYET_DA:
        raise ValueError("Chỉ có thể đặt làm bản đang dùng cho phiên bản ĐÃ DUYỆT.")
    db.execute("UPDATE color_versions SET is_active=0 WHERE color_id=%s", (v["color_id"],))
    db.execute("UPDATE color_versions SET is_active=1 WHERE id=%s", (version_id,))
    db.commit()


def delete(version_id):
    db = get_db()
    db.execute("DELETE FROM color_versions WHERE id=%s", (version_id,))
    db.commit()