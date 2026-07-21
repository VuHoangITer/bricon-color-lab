from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from models import get_db

# Tài khoản đã có hoạt động phải bị KHÓA đủ chừng này ngày mới được xóa vĩnh
# viễn (~6 tháng). Tài khoản CHƯA từng hoạt động gì thì xóa được ngay, không
# cần khóa/chờ.
DEACTIVATION_WAIT_DAYS = 180


def get_by_username(username):
    return get_db().execute(
        "SELECT * FROM users WHERE username = %s", (username,)
    ).fetchone()


def get_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()


def list_all():
    return get_db().execute("SELECT * FROM users ORDER BY username").fetchall()


def verify(username, password):
    u = get_by_username(username)
    if u and check_password_hash(u["password_hash"], password):
        return u
    return None


def create(username, password, full_name="", role="san_xuat"):
    db = get_db()
    db.execute(
        "INSERT INTO users (username, password_hash, full_name, role) VALUES (%s,%s,%s,%s)",
        (username, generate_password_hash(password), full_name, role),
    )
    db.commit()
    return db.execute("SELECT id FROM users WHERE username=%s", (username,)).fetchone()["id"]


def update_role(user_id, role):
    db = get_db()
    db.execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
    db.commit()


def reset_password(user_id, new_password):
    db = get_db()
    db.execute("UPDATE users SET password_hash=%s WHERE id=%s",
              (generate_password_hash(new_password), user_id))
    db.commit()


def has_activity(user_id):
    """True nếu tài khoản đã từng tạo/duyệt màu, tạo phiên bản, tải ảnh, hoặc
    có nhật ký hoạt động — dùng để quyết định xóa trực tiếp hay phải khóa
    trước. Tài khoản 'trắng' (chưa làm gì) mới được xóa ngay."""
    db = get_db()
    checks = [
        ("SELECT 1 FROM colors WHERE created_by=%s OR duyet_boi=%s LIMIT 1", (user_id, user_id)),
        ("SELECT 1 FROM color_versions WHERE created_by=%s OR duyet_boi=%s LIMIT 1", (user_id, user_id)),
        ("SELECT 1 FROM color_images WHERE uploaded_by=%s LIMIT 1", (user_id,)),
        ("SELECT 1 FROM activity_logs WHERE user_id=%s LIMIT 1", (user_id,)),
    ]
    return any(db.execute(q, params).fetchone() for q, params in checks)


def deactivate(user_id):
    """Khóa tài khoản — không đăng nhập được nữa, nhưng KHÔNG đụng tới dữ
    liệu/lịch sử đã tạo. Có thể mở khóa lại bất cứ lúc nào qua reactivate()."""
    db = get_db()
    db.execute(
        "UPDATE users SET is_active=0, deactivated_at=CURRENT_TIMESTAMP WHERE id=%s",
        (user_id,),
    )
    db.commit()


def reactivate(user_id):
    """Mở khóa lại tài khoản đã bị khóa."""
    db = get_db()
    db.execute("UPDATE users SET is_active=1, deactivated_at=NULL WHERE id=%s", (user_id,))
    db.commit()


def eligible_for_delete(user_row):
    """Trả về (eligible: bool, reason: str|None).
    - Tài khoản CHƯA từng hoạt động gì -> xóa được ngay.
    - Ngược lại: phải đang bị KHÓA và đã khóa đủ DEACTIVATION_WAIT_DAYS ngày
      mới được xóa vĩnh viễn.
    Khoảng thời gian đã trôi qua được tính NGAY TRONG Postgres (CURRENT_TIMESTAMP
    trừ đi deactivated_at) thay vì so với datetime.now() của Python — tránh
    lệch múi giờ giữa server chạy app và session Postgres (đã ép về giờ Việt
    Nam qua DB_TIMEZONE)."""
    if not has_activity(user_row["id"]):
        return True, None
    if user_row["is_active"]:
        return False, "Tài khoản đã có hoạt động — cần khóa tài khoản trước, đợi đủ 6 tháng mới xóa được."
    deactivated_at = user_row["deactivated_at"]
    if not deactivated_at:
        return False, "Không xác định được thời điểm khóa."
    row = get_db().execute(
        "SELECT CURRENT_TIMESTAMP - %s::timestamp AS elapsed", (deactivated_at,)
    ).fetchone()
    elapsed = row["elapsed"]  # psycopg2 trả sẵn dạng datetime.timedelta
    wait = timedelta(days=DEACTIVATION_WAIT_DAYS)
    if elapsed >= wait:
        return True, None
    remaining_days = (wait - elapsed).days + 1
    return False, f"Cần khóa đủ 6 tháng mới xóa được — còn khoảng {remaining_days} ngày."


def delete(user_id):
    """Xóa hẳn tài khoản. Gỡ tham chiếu ở các bảng khác (đặt NULL — tránh
    vướng khóa ngoại và KHÔNG xóa dữ liệu màu/phiên bản/ảnh đã tạo), đồng
    thời ẨN (không xóa) nhật ký hoạt động cũ của tài khoản này, rồi mới xóa
    dòng user. Gọi hàm này SAU KHI đã kiểm tra eligible_for_delete()."""
    db = get_db()
    db.execute("UPDATE colors SET created_by=NULL WHERE created_by=%s", (user_id,))
    db.execute("UPDATE colors SET duyet_boi=NULL WHERE duyet_boi=%s", (user_id,))
    db.execute("UPDATE color_versions SET created_by=NULL WHERE created_by=%s", (user_id,))
    db.execute("UPDATE color_versions SET duyet_boi=NULL WHERE duyet_boi=%s", (user_id,))
    db.execute("UPDATE color_images SET uploaded_by=NULL WHERE uploaded_by=%s", (user_id,))
    db.execute("UPDATE activity_logs SET hidden=1, user_id=NULL WHERE user_id=%s", (user_id,))
    db.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()