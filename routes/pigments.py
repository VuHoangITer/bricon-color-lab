from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import pigment as pigment_model
from models.activity_log import log
from routes.auth import permission_required

bp = Blueprint("pigments", __name__)


@bp.route("/pigments")
@permission_required("tao_pigment")
def index():
    return render_template("pigments/list.html",
                           pigments=pigment_model.all_with_usage())


@bp.route("/pigments/new", methods=["POST"])
@permission_required("tao_pigment")
def new():
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Tên pigment không được để trống.", "error")
    else:
        try:
            pid = pigment_model.create(name)
            log(session["user_id"], "THÊM PIGMENT", "pigment", pid, {"name": name})
            flash(f"Đã thêm pigment '{name}'.", "success")
        except Exception:
            flash("Pigment này đã tồn tại.", "error")
    return redirect(url_for("pigments.index"))


@bp.route("/pigments/<int:pigment_id>/edit", methods=["POST"])
@permission_required("sua_pigment")
def edit(pigment_id):
    p = pigment_model.get(pigment_id)
    if not p:
        flash("Không tìm thấy pigment.", "error")
        return redirect(url_for("pigments.index"))
    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Tên pigment không được để trống.", "error")
    elif name != p["name"]:
        try:
            pigment_model.rename(pigment_id, name)
            log(session["user_id"], "SỬA PIGMENT", "pigment", pigment_id,
                {"cu": p["name"], "moi": name})
            flash(f"Đã đổi tên '{p['name']}' → '{name}'.", "success")
        except Exception:
            flash("Tên này đã có pigment khác dùng.", "error")
    return redirect(url_for("pigments.index"))


@bp.route("/pigments/<int:pigment_id>/delete", methods=["POST"])
@permission_required("xoa_pigment")
def delete(pigment_id):
    p = pigment_model.get(pigment_id)
    if not p:
        flash("Không tìm thấy pigment.", "error")
        return redirect(url_for("pigments.index"))
    try:
        pigment_model.delete(pigment_id)
        log(session["user_id"], "XÓA PIGMENT", "pigment", pigment_id, {"name": p["name"]})
        flash(f"Đã xóa pigment '{p['name']}'.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("pigments.index"))
