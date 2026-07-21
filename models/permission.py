from models import get_db


def list_for_user(user_id):
    """Trả về set các permission được cấp thêm riêng cho user này."""
    rows = get_db().execute(
        "SELECT permission FROM user_permissions WHERE user_id = %s", (user_id,)
    ).fetchall()
    return {r["permission"] for r in rows}


def set_grants(user_id, permissions):
    """Ghi đè toàn bộ quyền cấp thêm cho user (dùng cho form quản lý user —
    checkbox nào không tick coi như bị gỡ)."""
    db = get_db()
    db.execute("DELETE FROM user_permissions WHERE user_id=%s", (user_id,))
    for p in permissions:
        db.execute(
            "INSERT INTO user_permissions (user_id, permission) VALUES (%s,%s) "
            "ON CONFLICT (user_id, permission) DO NOTHING",
            (user_id, p),
        )
    db.commit()