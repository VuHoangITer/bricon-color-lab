import re as _re
import time
from pathlib import Path
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, g, abort)
from werkzeug.utils import secure_filename
import config
from models import color as color_model
from models import color_version
from models import pigment as pigment_model
from models import image as image_model
from models.activity_log import log
from routes.auth import login_required, permission_required
from services.permissions import ROLE_ADMIN

bp = Blueprint("colors", __name__)


def _clean_hex(value):
    v = (value or "").strip().upper()
    return v if _re.fullmatch(r"#[0-9A-F]{6}", v) else None


def _parse_ratios(form, pigments):
    """Đọc input dạng % (0-100) từ form, trả về dict {pigment_id: phân số 0-1}."""
    ratios = {}
    for p in pigments:
        raw = (form.get(f"pigment_{p['id']}") or "").strip().replace(",", ".")
        try:
            val = float(raw) if raw else 0.0
        except ValueError:
            raise ValueError(f"Tỷ lệ của '{p['name']}' không hợp lệ: {raw}")
        if val < 0 or val > 100:
            raise ValueError(f"Tỷ lệ của '{p['name']}' phải trong khoảng 0–100%.")
        ratios[p["id"]] = val / 100.0
    return ratios


def _is_admin():
    """True nếu người thao tác là role admin — CHỈ admin được tự tay gõ/sửa
    mã màu. Các role khác luôn bị khóa: khi tạo màu thì dùng đúng mã được
    gợi ý tự động, khi sửa màu thì giữ nguyên mã cũ, bất kể form gửi gì lên."""
    user = g.get("current_user")
    return bool(user and user["role"] == ROLE_ADMIN)


def _can_self_approve():
    """True nếu người thao tác có quyền duyệt sẵn -> tự động ĐÃ DUYỆT,
    không phải qua bước CHỜ DUYỆT."""
    return "duyet_mau" in g.get("current_permissions", set())


def _suggested_ma_mau():
    """Khách hàng (role khach_hang, kể cả được cấp thêm quyền tao_mau) ->
    gợi ý dạng KH-{username}-NN, tách riêng khỏi dãy số nội bộ của công ty.
    Nội bộ (admin/quản lý/sản xuất) -> vẫn dùng dãy số như cũ (max+1)."""
    user = g.get("current_user")
    if user and user["role"] == "khach_hang":
        return color_model.next_ma_mau_khach_hang(user["username"])
    return color_model.next_ma_mau()


def _can_create_version(color):
    """Ai được tạo phiên bản mới cho màu này: có quyền sua_mau chung, hoặc
    là người tạo ra chính màu đó (kể cả khách hàng đặc biệt được cấp tao_mau)."""
    if "sua_mau" in g.get("current_permissions", set()):
        return True
    return color["created_by"] == session.get("user_id")


def _can_manage_images(color):
    return "upload_anh" in g.get("current_permissions", set()) or _can_create_version(color)


def _can_delete_color(color):
    """CHỈ admin được xóa màu — không còn cho Quản lý hay người tạo tự xóa
    nữa, bất kể màu đó đã có phiên bản dùng hay chưa."""
    return _is_admin()


def _can_delete_version(version):
    """duyet_mau (Admin/Quản lý) -> xóa được MỌI phiên bản (kể cả đã duyệt/
    đang dùng). Người tạo phiên bản chỉ xóa được bản nháp của mình (CHỜ
    DUYỆT/TỪ CHỐI) — không tự xóa được bản ĐÃ DUYỆT."""
    if "duyet_mau" in g.get("current_permissions", set()):
        return True
    uid = session.get("user_id")
    return version["created_by"] == uid and version["trang_thai_duyet"] != color_version.DUYET_DA


def _can_activate():
    """Chỉ Admin/Quản lý được chuyển đổi bản đang dùng — thay đổi này ảnh
    hưởng tới sản xuất thật nên cần người có quyền duyệt quyết định."""
    return "duyet_mau" in g.get("current_permissions", set())


def _can_edit_version(version):
    """Sửa TRỰC TIẾP 1 phiên bản (không tạo bản mới):
    - Admin/Quản lý (duyet_mau) -> sửa được BẤT KỲ phiên bản nào, kể cả
      đã duyệt/đang dùng — áp dụng ngay, không cần duyệt lại (họ vốn có
      quyền tự duyệt).
    - Người khác -> sửa được phiên bản CHỜ DUYỆT hoặc TỪ CHỐI do CHÍNH họ
      tạo (bản nháp chưa ai duyệt, hoặc bản bị từ chối — sửa xong sẽ tự
      gửi lại xin duyệt). Phiên bản đã duyệt/đang dùng thì không sửa tại
      chỗ được — phải tạo phiên bản mới."""
    if "duyet_mau" in g.get("current_permissions", set()):
        return True
    uid = session.get("user_id")
    return version["created_by"] == uid and version["trang_thai_duyet"] in (
        color_version.DUYET_CHO, color_version.DUYET_TU_CHOI)


@bp.route("/")
@login_required
def index():
    return render_template("colors/list.html",
                           items=color_model.list_all(),
                           pigments=pigment_model.all_ordered())


@bp.route("/colors/tim-mau-giong")
@login_required
def similar_search():
    hex_query = (request.args.get("hex") or "").strip()
    results = color_model.find_similar(hex_query, limit=24) if hex_query else []
    return render_template("colors/similar_search.html", hex_query=hex_query, results=results)


@bp.route("/colors/cua-toi")
@login_required
def mine():
    return render_template("colors/mine.html", items=color_version.list_mine(session["user_id"]))


@bp.route("/colors/cho-duyet")
@permission_required("duyet_mau")
def pending():
    return render_template("colors/pending.html", items=color_version.list_pending())


@bp.route("/colors/new", methods=["GET", "POST"])
@permission_required("tao_mau")
def new():
    pigments = pigment_model.all_ordered()
    if request.method == "POST":
        try:
            ratios = _parse_ratios(request.form, pigments)

            # Bắt buộc phải có ít nhất 1 ảnh khi tạo màu mới.
            f = request.files.get("image")
            if not f or not f.filename:
                raise ValueError("Cần tải lên ít nhất 1 ảnh khi tạo màu mới.")
            ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
            if ext not in config.ALLOWED_IMAGE_EXT:
                raise ValueError(f"Chỉ nhận ảnh: {', '.join(sorted(config.ALLOWED_IMAGE_EXT))}")

            auto_approve = _can_self_approve()
            # Chỉ admin được gõ tay mã màu — các role khác luôn bị khóa,
            # LUÔN lấy lại mã gợi ý tự động ngay lúc lưu (không tin giá trị
            # form gửi lên, tránh mã cũ/bị sửa tay qua devtools).
            ma_mau = request.form.get("ma_mau", "").strip() if _is_admin() else _suggested_ma_mau()
            color_id = color_model.create(
                ma_mau,
                request.form.get("ten_mau", ""),
                request.form.get("ghi_chu", ""),
                session["user_id"],
                hex_color=_clean_hex(request.form.get("hex_color")),
            )
            color_version.create_version(
                color_id, ratios, session["user_id"],
                ghi_chu=request.form.get("version_ghi_chu", ""),
                auto_approve=auto_approve,
            )

            config.IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)
            filename = f"color{color_id}_{int(time.time())}_{secure_filename(Path(f.filename).stem) or 'anh'}.{ext}"
            f.save(config.IMAGE_FOLDER / filename)
            image_model.create(color_id, f"uploads/images/{filename}",
                               request.form.get("loai_anh", "Khác"),
                               session["user_id"],
                               request.form.get("anh_ghi_chu", "").strip())

            log(session["user_id"], "TẠO MÀU", "color", color_id,
                {"ma_mau": ma_mau, "phien_ban": 1,
                 "trang_thai_duyet": "DA_DUYET" if auto_approve else "CHO_DUYET"})
            if auto_approve:
                flash("Đã tạo màu mới (tự động duyệt).", "success")
            else:
                flash("Đã tạo màu mới — phiên bản 1 đang CHỜ DUYỆT, cần Quản lý/Admin duyệt trước khi cân.", "success")
            return redirect(url_for("colors.detail", color_id=color_id))
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Lỗi: {e}", "error")
    return render_template("colors/form.html", pigments=pigments,
                           image_types=config.IMAGE_TYPES,
                           suggested_ma_mau=_suggested_ma_mau())


@bp.route("/colors/<int:color_id>")
@login_required
def detail(color_id):
    c = color_model.get(color_id)
    if not c:
        flash("Không tìm thấy màu này.", "error")
        return redirect(url_for("colors.index"))
    active = color_version.get_active(color_id)
    active_detail = color_version.detail(active["id"]) if active else None
    versions = color_version.list_for_color(color_id)
    similar_colors = color_model.find_similar(c["hex_color"], exclude_id=color_id, limit=6) if c["hex_color"] else []
    return render_template("colors/detail.html", color=c,
                           active=active, active_detail=active_detail,
                           versions=versions,
                           images=image_model.list_for_color(color_id),
                           image_types=config.IMAGE_TYPES,
                           ready_for_weighing=color_model.is_ready_for_weighing(color_id),
                           can_create_version=_can_create_version(c),
                           can_delete_color=_can_delete_color(c),
                           can_activate=_can_activate(),
                           version_has_pending=color_version.has_pending(color_id),
                           similar_colors=similar_colors,
                           can_edit_version=_can_edit_version)


@bp.route("/colors/<int:color_id>/versions/new", methods=["GET", "POST"])
@login_required
def new_version(color_id):
    c = color_model.get(color_id)
    if not c:
        flash("Không tìm thấy màu này.", "error")
        return redirect(url_for("colors.index"))
    if not _can_create_version(c):
        abort(403)
    if color_version.has_pending(color_id):
        flash("Màu này đang có 1 phiên bản CHỜ DUYỆT — xử lý xong bản đó (duyệt/từ chối) trước khi tạo bản mới.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))

    pigments = pigment_model.all_ordered()
    active = color_version.get_active(color_id)
    prefill = {}
    if active:
        prefill = {r["pigment_id"]: r["ty_le"] * 100 for r in color_version.get_ratio_rows(active["id"])}

    if request.method == "POST":
        try:
            ratios = _parse_ratios(request.form, pigments)
            old_ratios = {}
            if active:
                old_ratios = {r["name"]: r["ty_le"] for r in color_version.get_ratio_rows(active["id"])}
            new_ratios_named = {p["name"]: ratios[p["id"]] for p in pigments}

            # Chỉ admin được sửa mã màu ở đây — role khác gửi gì lên cũng
            # bị bỏ qua, giữ nguyên mã màu hiện tại của màu này.
            ma_mau = request.form.get("ma_mau", c["ma_mau"]).strip() if _is_admin() else c["ma_mau"]
            color_model.update_info(
                color_id,
                ma_mau,
                request.form.get("ten_mau", c["ten_mau"] or ""),
                request.form.get("ghi_chu", c["ghi_chu"] or ""),
                hex_color=_clean_hex(request.form.get("hex_color")),
            )

            auto_approve = _can_self_approve()
            version_id = color_version.create_version(
                color_id, ratios, session["user_id"],
                ghi_chu=request.form.get("version_ghi_chu", ""),
                auto_approve=auto_approve,
            )
            v = color_version.get(version_id)
            log(session["user_id"], "TẠO PHIÊN BẢN", "color", color_id,
                {"ma_mau": ma_mau, "phien_ban": v["version_number"],
                 "cu": old_ratios, "moi": new_ratios_named,
                 "trang_thai_duyet": "DA_DUYET" if auto_approve else "CHO_DUYET"})
            if auto_approve:
                flash(f"Đã tạo phiên bản {v['version_number']} (tự động duyệt, đang dùng).", "success")
            else:
                flash(f"Đã tạo phiên bản {v['version_number']} — đang CHỜ DUYỆT.", "success")
            return redirect(url_for("colors.detail", color_id=color_id))
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Lỗi: {e}", "error")

    return render_template("colors/version_form.html", color=c, pigments=pigments, values=prefill)


@bp.route("/colors/<int:color_id>/versions/<int:version_id>/edit", methods=["GET", "POST"])
@login_required
def edit_version(color_id, version_id):
    """Sửa TRỰC TIẾP tỷ lệ của 1 phiên bản đã tồn tại — không tạo bản mới,
    không đổi trạng thái duyệt/active (trừ trường hợp resubmit — xem dưới).
    Dùng cho sửa lỗi nhỏ/tinh chỉnh bản hiện tại (khác với 'Tạo phiên bản
    mới' — dùng khi thực sự đổi công thức)."""
    c = color_model.get(color_id)
    v = color_version.get(version_id)
    if not c or not v or v["color_id"] != color_id:
        flash("Không tìm thấy phiên bản này.", "error")
        return redirect(url_for("colors.index"))
    if not _can_edit_version(v):
        abort(403)

    # Chủ sở hữu (không phải Admin/Quản lý) sửa lại bản đã bị TỪ CHỐI ->
    # coi là gửi lại xin duyệt, tự chuyển về CHỜ DUYỆT. Admin/Quản lý sửa
    # thì áp dụng ngay, giữ nguyên trạng thái hiện tại (không đổi gì).
    is_resubmit = ("duyet_mau" not in g.get("current_permissions", set())
                   and v["trang_thai_duyet"] == color_version.DUYET_TU_CHOI)

    pigments = pigment_model.all_ordered()
    prefill = {r["pigment_id"]: r["ty_le"] * 100 for r in color_version.get_ratio_rows(version_id)}

    if request.method == "POST":
        try:
            ratios = _parse_ratios(request.form, pigments)
            old_ratios_named = {p["name"]: (prefill.get(p["id"], 0) or 0) / 100.0 for p in pigments}
            new_ratios_named = {p["name"]: ratios[p["id"]] for p in pigments}
            # Chỉ admin được sửa mã màu ở đây — role khác gửi gì lên cũng
            # bị bỏ qua, giữ nguyên mã màu hiện tại của màu này.
            ma_mau = request.form.get("ma_mau", c["ma_mau"]).strip() if _is_admin() else c["ma_mau"]
            color_model.update_info(
                color_id,
                ma_mau,
                request.form.get("ten_mau", c["ten_mau"] or ""),
                request.form.get("ghi_chu", c["ghi_chu"] or ""),
                hex_color=_clean_hex(request.form.get("hex_color")),
            )
            color_version.update_ratios(
                version_id, ratios,
                ghi_chu=request.form.get("version_ghi_chu", v["ghi_chu"] or ""),
                resubmit=is_resubmit,
            )
            log(session["user_id"], "SỬA PHIÊN BẢN", "color", color_id,
                {"ma_mau": ma_mau,
                 "phien_ban": v["version_number"], "gui_lai": is_resubmit,
                 "cu": old_ratios_named, "moi": new_ratios_named})
            if is_resubmit:
                flash(f"Đã cập nhật và GỬI LẠI phiên bản {v['version_number']} — đang CHỜ DUYỆT.", "success")
            else:
                flash(f"Đã cập nhật phiên bản {v['version_number']}.", "success")
            return redirect(url_for("colors.detail", color_id=color_id))
        except ValueError as e:
            flash(str(e), "error")
        except Exception as e:
            flash(f"Lỗi: {e}", "error")

    return render_template("colors/version_edit_form.html", color=c, version=v,
                           pigments=pigments, values=prefill, is_resubmit=is_resubmit)


@bp.route("/colors/<int:color_id>/versions/<int:version_id>")
@login_required
def version_detail(color_id, version_id):
    c = color_model.get(color_id)
    v = color_version.get(version_id)
    if not c or not v or v["color_id"] != color_id:
        flash("Không tìm thấy phiên bản này.", "error")
        return redirect(url_for("colors.index"))
    d = color_version.detail(version_id)
    return render_template("colors/version_detail.html", color=c, d=d,
                           can_activate=_can_activate(),
                           can_delete_version=_can_delete_version(v),
                           can_edit_version=_can_edit_version(v))


@bp.route("/colors/<int:color_id>/versions/<int:version_id>/approve", methods=["POST"])
@permission_required("duyet_mau")
def approve_version(color_id, version_id):
    v = color_version.get(version_id)
    if not v or v["color_id"] != color_id:
        flash("Không tìm thấy phiên bản này.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    d = color_version.detail(version_id)
    if d["status"] != "ĐẠT":
        flash(f"Không thể duyệt — tổng pigment đang {d['status']}, cần đúng 100%.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    color_version.approve(version_id, session["user_id"])
    log(session["user_id"], "DUYỆT PHIÊN BẢN", "color", color_id, {"phien_ban": v["version_number"]})
    flash("Đã duyệt phiên bản — trở thành bản đang dùng.", "success")
    return redirect(url_for("colors.detail", color_id=color_id))


@bp.route("/colors/<int:color_id>/versions/<int:version_id>/reject", methods=["POST"])
@permission_required("duyet_mau")
def reject_version(color_id, version_id):
    v = color_version.get(version_id)
    if not v or v["color_id"] != color_id:
        flash("Không tìm thấy phiên bản này.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    reason = (request.form.get("ly_do") or "").strip()
    color_version.reject(version_id, session["user_id"], reason)
    log(session["user_id"], "TỪ CHỐI PHIÊN BẢN", "color", color_id,
        {"phien_ban": v["version_number"], "ly_do": reason})
    flash("Đã từ chối phiên bản.", "success")
    return redirect(url_for("colors.detail", color_id=color_id))


@bp.route("/colors/<int:color_id>/versions/<int:version_id>/activate", methods=["POST"])
@permission_required("duyet_mau")
def activate_version(color_id, version_id):
    v = color_version.get(version_id)
    if not v or v["color_id"] != color_id:
        flash("Không tìm thấy phiên bản này.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    try:
        color_version.activate(version_id)
        log(session["user_id"], "DÙNG LẠI PHIÊN BẢN", "color", color_id,
            {"phien_ban": v["version_number"]})
        flash(f"Đã đặt phiên bản {v['version_number']} làm bản đang dùng.", "success")
    except ValueError as e:
        flash(str(e), "error")
    return redirect(url_for("colors.detail", color_id=color_id))


@bp.route("/colors/<int:color_id>/versions/<int:version_id>/delete", methods=["POST"])
@login_required
def delete_version(color_id, version_id):
    v = color_version.get(version_id)
    if not v or v["color_id"] != color_id:
        flash("Không tìm thấy phiên bản này.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    if not _can_delete_version(v):
        abort(403)
    # Nếu đây là PHIÊN BẢN DUY NHẤT của màu, xóa nó = xóa luôn cả màu (xem
    # đoạn cascade bên dưới) -> phải là admin, đồng bộ với quy định "chỉ
    # admin được xóa màu". Không chặn thì Quản lý (có quyền xóa phiên bản)
    # lách qua đường này để xóa được màu.
    if len(color_version.list_for_color(color_id)) == 1 and not _is_admin():
        flash("Đây là phiên bản duy nhất của màu này — xóa sẽ xóa luôn cả màu, chỉ Admin được thực hiện.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    was_active = bool(v["is_active"])
    vnum = v["version_number"]
    color_version.delete(version_id)
    log(session["user_id"], "XÓA PHIÊN BẢN", "color", color_id, {"phien_ban": vnum})

    # Nếu vừa xóa PHIÊN BẢN CUỐI CÙNG của màu -> xóa luôn cả màu. Không làm
    # vậy sẽ để lại 1 'xác' màu 0 phiên bản: không hiện ở đâu trong giao
    # diện (thư viện cần có bản active, "Của tôi" liệt kê theo phiên bản),
    # nhưng mã màu vẫn bị chiếm giữ do ràng buộc UNIQUE — tạo lại đúng mã
    # đó sau này sẽ báo lỗi trùng mà không ai hiểu vì sao.
    if not color_version.list_for_color(color_id):
        c = color_model.get(color_id)
        ma_mau = c["ma_mau"]
        _delete_color_with_files(c)
        log(session["user_id"], "XÓA MÀU", "color", color_id,
            {"ma_mau": ma_mau, "ly_do": "Xóa phiên bản cuối cùng của màu"})
        flash(f"Đã xóa phiên bản {vnum} — đây là phiên bản cuối cùng nên màu '{ma_mau}' cũng đã được xóa luôn.", "success")
        return redirect(url_for("colors.index"))

    if was_active:
        flash(f"Đã xóa phiên bản {vnum} — hiện chưa có bản nào đang dùng, chọn 1 bản ĐÃ DUYỆT khác để dùng lại.", "success")
    else:
        flash(f"Đã xóa phiên bản {vnum}.", "success")
    return redirect(url_for("colors.detail", color_id=color_id))


@bp.route("/colors/<int:color_id>/upload-image", methods=["POST"])
@login_required
def upload_image(color_id):
    c = color_model.get(color_id)
    if not c:
        flash("Không tìm thấy màu này.", "error")
        return redirect(url_for("colors.index"))
    if not _can_manage_images(c):
        abort(403)
    f = request.files.get("image")
    if not f or not f.filename:
        flash("Chưa chọn file ảnh.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in config.ALLOWED_IMAGE_EXT:
        flash(f"Chỉ nhận ảnh: {', '.join(sorted(config.ALLOWED_IMAGE_EXT))}", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    config.IMAGE_FOLDER.mkdir(parents=True, exist_ok=True)
    filename = f"color{color_id}_{int(time.time())}_{secure_filename(Path(f.filename).stem) or 'anh'}.{ext}"
    f.save(config.IMAGE_FOLDER / filename)
    rel = f"uploads/images/{filename}"
    image_model.create(color_id, rel,
                       request.form.get("loai_anh", "Khác"),
                       session["user_id"],
                       request.form.get("ghi_chu", "").strip())
    log(session["user_id"], "TẢI ẢNH", "color", color_id,
        {"file": rel, "loai_anh": request.form.get("loai_anh")})
    flash("Đã tải ảnh lên.", "success")
    return redirect(url_for("colors.detail", color_id=color_id))



def _delete_color_with_files(c):
    """Xóa hẳn 1 màu + dọn file ảnh/QR liên quan trên đĩa. Dùng chung cho cả
    route xóa màu trực tiếp và trường hợp xóa phiên bản cuối cùng khiến màu
    không còn phiên bản nào (tránh để lại 'xác' màu 0 phiên bản vẫn chiếm
    giữ mã màu — không hiện ở đâu trong giao diện nhưng vẫn chặn tạo lại
    đúng mã đó do ràng buộc UNIQUE)."""
    for img in image_model.list_for_color(c["id"]):
        try:
            (config.IMAGE_FOLDER / Path(img["file_path"]).name).unlink(missing_ok=True)
        except Exception:
            pass
    if c["qr_code_path"]:
        try:
            (config.QR_FOLDER / Path(c["qr_code_path"]).name).unlink(missing_ok=True)
        except Exception:
            pass
    color_model.delete(c["id"])


@bp.route("/colors/<int:color_id>/delete", methods=["POST"])
@login_required
def delete(color_id):
    c = color_model.get(color_id)
    if not c:
        flash("Không tìm thấy màu này.", "error")
        return redirect(url_for("colors.index"))
    if not _can_delete_color(c):
        abort(403)

    ma_mau = c["ma_mau"]
    _delete_color_with_files(c)
    log(session["user_id"], "XÓA MÀU", "color", color_id, {"ma_mau": ma_mau})
    flash(f"Đã xóa màu '{ma_mau}'.", "success")
    return redirect(url_for("colors.index"))


@bp.route("/colors/<int:color_id>/images/<int:image_id>/delete", methods=["POST"])
@login_required
def delete_image(color_id, image_id):
    img = image_model.get(image_id)
    if not img or img["color_id"] != color_id:
        flash("Không tìm thấy ảnh này.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    # CHỈ admin được xóa ảnh — không còn cho người tự upload hay Quản lý
    # (duyet_mau) xóa nữa.
    if not _is_admin():
        abort(403)
    image_model.delete(image_id)
    try:
        (config.IMAGE_FOLDER / Path(img["file_path"]).name).unlink(missing_ok=True)
    except Exception:
        pass
    log(session["user_id"], "XÓA ẢNH", "color", color_id, {"file": img["file_path"]})
    flash("Đã xóa ảnh.", "success")
    return redirect(url_for("colors.detail", color_id=color_id))