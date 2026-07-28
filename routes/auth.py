from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, g, abort)
from werkzeug.security import check_password_hash
from models import user as user_model
from models import permission as permission_model
from models import color_version
from services.permissions import effective_permissions, ROLE_LABELS, ROLE_ADMIN

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def permission_required(permission):
    """Bắt buộc đăng nhập VÀ có quyền cụ thể (đã tính role + quyền cấp thêm)."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("auth.login", next=request.path))
            if permission not in g.get("current_permissions", set()):
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@bp.before_app_request
def load_current_user():
    uid = session.get("user_id")
    if uid:
        user = user_model.get_by_id(uid)
        if not user or not user["is_active"]:
            # Tài khoản đã bị khóa/xóa ngay trong lúc đang đăng nhập -> đá ra
            # ngay, không đợi họ tự đăng xuất.
            session.clear()
            g.current_user = None
            g.current_permissions = set()
            g.my_pending_count = 0
            g.approval_pending_count = 0
            return
        g.current_user = user
        extra = permission_model.list_for_user(uid)
        g.current_permissions = effective_permissions(g.current_user, extra)
        g.my_pending_count = (
            color_version.count_mine_pending_or_rejected(uid)
            if "tao_mau" in g.current_permissions else 0
        )
        g.approval_pending_count = (
            color_version.count_pending()
            if "duyet_mau" in g.current_permissions else 0
        )
    else:
        g.current_user = None
        g.current_permissions = set()
        g.my_pending_count = 0
        g.approval_pending_count = 0


@bp.app_context_processor
def inject_template_helpers():
    return {
        "can": lambda p: p in g.get("current_permissions", set()),
        "role_label": lambda r: ROLE_LABELS.get(r, r),
        "is_admin": lambda: bool(g.get("current_user") and g.current_user["role"] == ROLE_ADMIN),
    }


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = user_model.verify(request.form.get("username", "").strip(),
                              request.form.get("password", ""))
        if u and not u["is_active"]:
            flash("Tài khoản này đã bị khóa. Liên hệ Admin/Quản lý nếu cần hỗ trợ.", "error")
        elif u:
            session["user_id"] = u["id"]
            flash(f"Xin chào {u['full_name'] or u['username']}!", "success")
            nxt = request.args.get("next") or url_for("colors.index")
            return redirect(nxt)
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu.", "error")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Đã đăng xuất.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/doi-mat-khau", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("mat_khau_hien_tai", "")
        new = request.form.get("mat_khau_moi", "")
        confirm = request.form.get("xac_nhan", "")
        user = user_model.get_by_id(session["user_id"])
        if not check_password_hash(user["password_hash"], current):
            flash("Mật khẩu hiện tại không đúng.", "error")
        elif len(new) < 4:
            flash("Mật khẩu mới quá ngắn (tối thiểu 4 ký tự).", "error")
        elif new != confirm:
            flash("Xác nhận mật khẩu mới không khớp.", "error")
        else:
            user_model.reset_password(session["user_id"], new)
            flash("Đã đổi mật khẩu thành công.", "success")
            return redirect(url_for("colors.index"))
    return render_template("change_password.html")