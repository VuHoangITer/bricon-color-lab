from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import user as user_model
from models import permission as permission_model
from models.activity_log import log
from routes.auth import permission_required
from services.permissions import (ROLES, ROLE_LABELS, GRANTABLE_EXTRA, PERM_LABELS,
                                  ROLE_KHACH_HANG, ROLE_DEFAULTS)

bp = Blueprint("users", __name__)


@bp.route("/users")
@permission_required("quan_ly_nguoi_dung")
def index():
    users = user_model.list_all()
    grants = {u["id"]: permission_model.list_for_user(u["id"]) for u in users}
    role_permissions = {
        r: sorted(PERM_LABELS.get(p, p) for p in ROLE_DEFAULTS[r])
        for r in ROLES
    }
    delete_status = {u["id"]: dict(zip(("eligible", "reason"), user_model.eligible_for_delete(u)))
                      for u in users}
    return render_template("users/list.html", users=users, grants=grants,
                           roles=ROLES, role_labels=ROLE_LABELS,
                           grantable=GRANTABLE_EXTRA, perm_labels=PERM_LABELS,
                           khach_hang_role=ROLE_KHACH_HANG,
                           role_permissions=role_permissions,
                           delete_status=delete_status)


@bp.route("/users/new", methods=["POST"])
@permission_required("quan_ly_nguoi_dung")
def new():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    full_name = (request.form.get("full_name") or "").strip()
    role = request.form.get("role") or "san_xuat"
    if role not in ROLES:
        role = "san_xuat"
    if not username or not password:
        flash("Thiếu tên đăng nhập hoặc mật khẩu.", "error")
        return redirect(url_for("users.index"))
    try:
        uid = user_model.create(username, password, full_name, role)
        log(session["user_id"], "TẠO USER", "user", uid, {"username": username, "role": role})
        flash(f"Đã tạo tài khoản '{username}'.", "success")
    except Exception:
        flash("Tên đăng nhập đã tồn tại.", "error")
    return redirect(url_for("users.index"))


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@permission_required("quan_ly_nguoi_dung")
def set_role(user_id):
    role = request.form.get("role") or "san_xuat"
    if role not in ROLES:
        flash("Vai trò không hợp lệ.", "error")
        return redirect(url_for("users.index"))
    user_model.update_role(user_id, role)
    log(session["user_id"], "SỬA VAI TRÒ", "user", user_id, {"role": role})
    flash("Đã cập nhật vai trò.", "success")
    return redirect(url_for("users.index"))


@bp.route("/users/<int:user_id>/permissions", methods=["POST"])
@permission_required("quan_ly_nguoi_dung")
def set_permissions(user_id):
    """Chỉ dùng để cấp thêm quyền đặc biệt (vd. khách hàng đặc biệt được
    tao_mau/tao_pigment). Checkbox nào không tick sẽ bị gỡ khỏi user này."""
    selected = set(request.form.getlist("perm")) & GRANTABLE_EXTRA
    permission_model.set_grants(user_id, selected)
    log(session["user_id"], "SỬA QUYỀN RIÊNG", "user", user_id, {"quyen": sorted(selected)})
    flash("Đã cập nhật quyền riêng.", "success")
    return redirect(url_for("users.index"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@permission_required("quan_ly_nguoi_dung")
def reset_password(user_id):
    new_password = request.form.get("password") or ""
    if len(new_password) < 4:
        flash("Mật khẩu quá ngắn (tối thiểu 4 ký tự).", "error")
        return redirect(url_for("users.index"))
    user_model.reset_password(user_id, new_password)
    log(session["user_id"], "ĐẶT LẠI MẬT KHẨU", "user", user_id, {})
    flash("Đã đặt lại mật khẩu.", "success")
    return redirect(url_for("users.index"))


@bp.route("/users/<int:user_id>/deactivate", methods=["POST"])
@permission_required("quan_ly_nguoi_dung")
def deactivate(user_id):
    if user_id == session["user_id"]:
        flash("Không thể khóa tài khoản đang đăng nhập.", "error")
        return redirect(url_for("users.index"))
    u = user_model.get_by_id(user_id)
    if not u:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect(url_for("users.index"))
    user_model.deactivate(user_id)
    log(session["user_id"], "KHÓA TÀI KHOẢN", "user", user_id, {"username": u["username"]})
    flash(f"Đã khóa tài khoản '{u['username']}'.", "success")
    return redirect(url_for("users.index"))


@bp.route("/users/<int:user_id>/reactivate", methods=["POST"])
@permission_required("quan_ly_nguoi_dung")
def reactivate(user_id):
    u = user_model.get_by_id(user_id)
    if not u:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect(url_for("users.index"))
    user_model.reactivate(user_id)
    log(session["user_id"], "MỞ KHÓA TÀI KHOẢN", "user", user_id, {"username": u["username"]})
    flash(f"Đã mở khóa tài khoản '{u['username']}'.", "success")
    return redirect(url_for("users.index"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@permission_required("quan_ly_nguoi_dung")
def delete(user_id):
    if user_id == session["user_id"]:
        flash("Không thể xóa tài khoản đang đăng nhập.", "error")
        return redirect(url_for("users.index"))
    u = user_model.get_by_id(user_id)
    if not u:
        flash("Không tìm thấy tài khoản.", "error")
        return redirect(url_for("users.index"))
    eligible, reason = user_model.eligible_for_delete(u)
    if not eligible:
        flash(reason, "error")
        return redirect(url_for("users.index"))
    user_model.delete(user_id)
    log(session["user_id"], "XÓA USER", "user", user_id, {"username": u["username"]})
    flash(f"Đã xóa vĩnh viễn tài khoản '{u['username']}'.", "success")
    return redirect(url_for("users.index"))