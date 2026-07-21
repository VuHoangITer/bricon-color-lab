import math
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import config
from models import get_db
from models import image as image_model
from models.activity_log import log
from routes.auth import permission_required

bp = Blueprint("images", __name__)

PER_PAGE = 48  # bội số của lưới ảnh cho đẹp (4/6 ảnh mỗi hàng)


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


@bp.route("/anh")
@permission_required("quan_ly_anh")
def index():
    color_id = request.args.get("color_id", type=int)
    uploaded_by = request.args.get("uploaded_by", type=int)
    loai_anh = (request.args.get("loai_anh") or "").strip() or None

    total = image_model.count_all(color_id=color_id, uploaded_by=uploaded_by, loai_anh=loai_anh)
    total_pages = max(1, math.ceil(total / PER_PAGE))
    page = request.args.get("page", 1, type=int) or 1
    page = min(max(1, page), total_pages)

    images = image_model.list_all(page=page, per_page=PER_PAGE,
                                   color_id=color_id, uploaded_by=uploaded_by, loai_anh=loai_anh)
    db = get_db()
    colors = db.execute("SELECT id, ma_mau, ten_mau FROM colors ORDER BY id").fetchall()
    users = db.execute("SELECT id, username, full_name FROM users ORDER BY username").fetchall()
    return render_template("images/list.html", images=images, colors=colors, users=users,
                           image_types=config.IMAGE_TYPES,
                           f_color=color_id, f_user=uploaded_by, f_loai=loai_anh,
                           page=page, total_pages=total_pages, total=total,
                           page_range=_page_range(page, total_pages))


@bp.route("/anh/<int:image_id>/delete", methods=["POST"])
@permission_required("quan_ly_anh")
def delete(image_id):
    img = image_model.get(image_id)
    if not img:
        flash("Không tìm thấy ảnh này.", "error")
        return redirect(url_for("images.index"))
    image_model.delete(image_id)
    try:
        (config.IMAGE_FOLDER / Path(img["file_path"]).name).unlink(missing_ok=True)
    except Exception:
        pass
    log(session["user_id"], "XÓA ẢNH", "color", img["color_id"], {"file": img["file_path"]})
    flash("Đã xóa ảnh.", "success")
    return redirect(url_for("images.index", page=request.args.get("page", type=int)))