from flask import Blueprint, render_template, abort, request, flash
from models import weighing as weighing_model
from models import color as color_model
from models import image as image_model

bp = Blueprint("public", __name__)


@bp.route("/phieu-can/<token>")
def phieu_can(token):
    """Trang CÔNG KHAI — không yêu cầu đăng nhập. Hiện đúng thông tin đã
    CHỐT tại thời điểm tạo phiếu cân (mã màu, tên màu, tổng thành phẩm, tỷ
    lệ pigment, người tạo, ngày) — không đổi theo công thức màu về sau, dù
    màu/tài khoản đó có bị sửa hay xóa. Chỉ hiện đúng các dòng này, không
    hiện bảng chi tiết pigment hay bất kỳ thông tin nào khác."""
    rec = weighing_model.get_by_token(token)
    if not rec:
        abort(404)
    return render_template("public/phieu_can.html", rec=rec)


@bp.route("/bang-mau")
def bang_mau():
    """Bảng màu CÔNG KHAI cho khách xem — không cần đăng nhập. Chỉ hiện mã
    màu/tên màu/HEX/Lab (qua color_model.list_public()) — KHÔNG có công
    thức/tỷ lệ pigment ở đâu trên trang này."""
    return render_template("public/bang_mau.html", items=color_model.list_public())


@bp.route("/bang-mau/<int:color_id>")
def bang_mau_detail(color_id):
    """Chi tiết 1 màu — trang công khai. get_public() chỉ trả về màu đang
    có phiên bản ĐANG DÙNG (đã duyệt), không thì 404 — khách không thấy
    được màu đang chờ duyệt/chưa chính thức. Có kèm gợi ý màu gần giống
    trong chính bảng màu công khai này (so bằng Lab/HEX, không liên quan
    công thức)."""
    c = color_model.get_public(color_id)
    if not c:
        abort(404)
    target_lab = color_model.get_lab(c)
    similar = (color_model.find_similar(lab=target_lab, exclude_id=color_id, limit=6)
               if target_lab else [])
    return render_template("public/bang_mau_detail.html", color=c,
                           images=image_model.list_for_color(color_id),
                           similar_colors=similar)


@bp.route("/bang-mau/tim-mau-giong")
def bang_mau_tim_mau_giong():
    """Tìm màu gần giống — bản CÔNG KHAI của colors.similar_search, cho
    khách nhập mã HEX hoặc Lab đo từ mẫu gạch của họ để so với bảng màu,
    không cần đăng nhập. Chỉ hiện mã màu/tên/HEX/Lab/% khớp — không có
    công thức pigment."""
    hex_query = (request.args.get("hex") or "").strip()
    raw_l = (request.args.get("lab_l") or "").strip()
    raw_a = (request.args.get("lab_a") or "").strip()
    raw_b = (request.args.get("lab_b") or "").strip()
    lab_query = None
    if raw_l and raw_a and raw_b:
        try:
            lab_query = (float(raw_l.replace(",", ".")),
                         float(raw_a.replace(",", ".")),
                         float(raw_b.replace(",", ".")))
        except ValueError:
            flash("Giá trị L*/a*/b* không hợp lệ.", "error")

    results = []
    if lab_query:
        results = color_model.find_similar(lab=lab_query, limit=24)
    elif hex_query:
        results = color_model.find_similar(hex_color=hex_query, limit=24)
    return render_template("public/tim_mau_giong.html", hex_query=hex_query,
                           raw_l=raw_l, raw_a=raw_a, raw_b=raw_b,
                           lab_query=lab_query, results=results)