import math
from flask import Blueprint, render_template, request
from models.activity_log import list_logs, count_logs, humanize
from models import get_db
from routes.auth import permission_required

bp = Blueprint("logs", __name__)

PER_PAGE = 50


def _page_range(page, total_pages, window=2):
    """Danh sách số trang rút gọn kiểu [1, '…', 4, 5, 6, '…', 20]."""
    pages = {1, total_pages}
    for p in range(page - window, page + window + 1):
        if 1 <= p <= total_pages:
            pages.add(p)
    ordered = sorted(pages)
    result, prev = [], None
    for p in ordered:
        if prev is not None and p - prev > 1:
            result.append("…")
        result.append(p)
        prev = p
    return result


@bp.route("/logs")
@permission_required("xem_nhat_ky")
def index():
    user_id = request.args.get("user_id", type=int)
    color_id = request.args.get("color_id", type=int)
    target_type, target_id = (("color", color_id) if color_id else (None, None))

    total = count_logs(user_id=user_id, target_type=target_type, target_id=target_id)
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = request.args.get("page", 1, type=int) or 1
    page = min(max(1, page), total_pages)

    rows = list_logs(user_id=user_id, target_type=target_type, target_id=target_id,
                      page=page, per_page=PER_PAGE)
    logs = [dict(r, human_detail=humanize(r["action"], r["detail"])) for r in rows]
    db = get_db()
    users = db.execute("SELECT id, username, full_name FROM users ORDER BY username").fetchall()
    colors = db.execute("SELECT id, ma_mau, ten_mau FROM colors ORDER BY id").fetchall()
    return render_template("logs/list.html", logs=logs, users=users,
                           colors=colors, f_user=user_id, f_color=color_id,
                           page=page, total_pages=total_pages, total=total,
                           page_range=_page_range(page, total_pages))