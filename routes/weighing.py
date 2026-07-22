"""Phiếu cân dạng stateless — tính trong phiên, in/xuất PDF được,
KHÔNG lưu lịch sử vào DB, chỉ ghi nhật ký hoạt động."""
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, session, g, send_file)
import config
from models import color as color_model
from models import color_version
from models import weighing as weighing_model
from models.activity_log import log
from routes.auth import permission_required
from services import calculator, pdf_service, qr_service

bp = Blueprint("weighing", __name__)

DEFAULT_TY_LE_PIGMENT = 4.0  # % — mặc định cố định theo yêu cầu


def _parse_params(src):
    tong = float((src.get("tong_thanh_pham") or "0").replace(",", "."))
    ty_le = float((src.get("ty_le_pigment") or str(DEFAULT_TY_LE_PIGMENT)).replace(",", ".")) / 100.0
    if tong <= 0:
        raise ValueError("Tổng thành phẩm phải lớn hơn 0.")
    if not (0 < ty_le < 1):
        raise ValueError("Tỷ lệ pigment phải trong khoảng 0–100%.")
    return tong, ty_le


def _build_d(color_id):
    """Ghép color + phiên bản đang dùng thành 1 dict tương thích với
    template cũ (d.color, d.pigment_rows, d.active_rows, d.status, d.total)."""
    c = color_model.get(color_id)
    if not c:
        return None
    active = color_version.get_active(color_id)
    if not active:
        return {"color": c, "pigment_rows": [], "active_rows": [], "total": 0, "status": "CHƯA CÓ BẢN DÙNG"}
    active_detail = color_version.detail(active["id"])
    return {"color": c, **active_detail}


@bp.route("/colors/<int:color_id>/weighing/new", methods=["GET", "POST"])
@permission_required("tao_phieu_can")
def new(color_id):
    d = _build_d(color_id)
    if not d:
        flash("Không tìm thấy màu này.", "error")
        return redirect(url_for("colors.index"))
    if not color_model.is_ready_for_weighing(color_id):
        flash("Công thức chưa ĐƯỢC DUYỆT hoặc chưa ĐẠT 100% — không thể tạo phiếu cân.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    if request.method == "POST":
        try:
            tong, ty_le = _parse_params(request.form)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("weighing/form.html", d=d,
                                   default_ty_le=DEFAULT_TY_LE_PIGMENT)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        nguoi_tao = (g.current_user["full_name"] or g.current_user["username"]) if g.current_user else "—"
        token = weighing_model.create(
            color_id=color_id, ma_mau=d["color"]["ma_mau"], ten_mau=d["color"]["ten_mau"],
            tong_thanh_pham_g=tong, ty_le_pigment=ty_le, nguoi_tao=nguoi_tao,
            ngay_tao=now, created_by=session["user_id"])
        log(session["user_id"], "TẠO PHIẾU CÂN", "color", color_id,
            {"ma_mau": d["color"]["ma_mau"], "tong_g": tong, "ty_le_pigment": ty_le})
        return redirect(url_for("weighing.result", color_id=color_id,
                                tong_thanh_pham=tong, ty_le_pigment=ty_le * 100, record=token))
    return render_template("weighing/form.html", d=d,
                           default_ty_le=DEFAULT_TY_LE_PIGMENT)


@bp.route("/colors/<int:color_id>/weighing/result")
@permission_required("tao_phieu_can")
def result(color_id):
    d = _build_d(color_id)
    if not d:
        flash("Không tìm thấy màu này.", "error")
        return redirect(url_for("colors.index"))
    if not color_model.is_ready_for_weighing(color_id):
        flash("Công thức chưa ĐƯỢC DUYỆT — không thể xem phiếu cân.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    try:
        tong, ty_le = _parse_params(request.args)
    except ValueError:
        return redirect(url_for("weighing.new", color_id=color_id))
    calc = calculator.calculate(tong, ty_le, d["pigment_rows"])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    qr_data_uri = None
    record_token = request.args.get("record")
    if record_token:
        qr_url = config.BASE_URL + url_for("public.phieu_can", token=record_token)
        qr_data_uri = qr_service.generate_data_uri(qr_url)

    return render_template("weighing/result.html", d=d, calc=calc, now=now, qr_data_uri=qr_data_uri)


@bp.route("/colors/<int:color_id>/weighing/pdf")
@permission_required("xuat_pdf")
def pdf(color_id):
    d = _build_d(color_id)
    if not d:
        flash("Không tìm thấy màu này.", "error")
        return redirect(url_for("colors.index"))
    if not color_model.is_ready_for_weighing(color_id):
        flash("Công thức chưa ĐƯỢC DUYỆT — không thể xuất PDF.", "error")
        return redirect(url_for("colors.detail", color_id=color_id))
    try:
        tong, ty_le = _parse_params(request.args)
    except ValueError:
        return redirect(url_for("weighing.new", color_id=color_id))
    calc = calculator.calculate(tong, ty_le, d["pigment_rows"])
    user = g.current_user
    info = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "nguoi_tao": (user["full_name"] or user["username"]) if user else "—",
    }
    filepath = pdf_service.export_weighing_sheet(info, calc, d["color"])
    log(session["user_id"], "XUẤT PDF", "color", color_id,
        {"ma_mau": d["color"]["ma_mau"], "tong_g": tong})
    return send_file(filepath, as_attachment=True,
                     download_name=f"phieu_can_{d['color']['ma_mau']}.pdf")