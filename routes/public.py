from flask import Blueprint, render_template, abort
from models import weighing as weighing_model

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