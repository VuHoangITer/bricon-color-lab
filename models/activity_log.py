import json
from markupsafe import Markup, escape
from models import get_db


def log(user_id, action, target_type=None, target_id=None, detail=None):
    if isinstance(detail, (dict, list)):
        detail = json.dumps(detail, ensure_ascii=False)
    db = get_db()
    db.execute(
        "INSERT INTO activity_logs (user_id, action, target_type, target_id, detail) VALUES (%s,%s,%s,%s,%s)",
        (user_id, action, target_type, target_id, detail),
    )
    db.commit()


def list_logs(user_id=None, target_type=None, target_id=None, page=1, per_page=50,
              include_hidden=False):
    """Trả về 1 trang kết quả (mới nhất trước). page bắt đầu từ 1.
    Mặc định KHÔNG hiện log đã bị ẩn (hidden=1 — log của tài khoản đã bị xóa
    vĩnh viễn)."""
    page = max(1, page)
    q = """SELECT l.*, u.username, u.full_name
           FROM activity_logs l LEFT JOIN users u ON u.id = l.user_id WHERE 1=1"""
    params = []
    if not include_hidden:
        q += " AND l.hidden = 0"
    if user_id:
        q += " AND l.user_id = %s"
        params.append(user_id)
    if target_type:
        q += " AND l.target_type = %s"
        params.append(target_type)
    if target_id:
        q += " AND l.target_id = %s"
        params.append(target_id)
    q += " ORDER BY l.id DESC LIMIT %s OFFSET %s"
    params += [per_page, (page - 1) * per_page]
    return get_db().execute(q, params).fetchall()


def count_logs(user_id=None, target_type=None, target_id=None, include_hidden=False):
    """Tổng số bản ghi khớp bộ lọc — dùng để tính số trang cho phân trang."""
    q = "SELECT COUNT(*) AS n FROM activity_logs l WHERE 1=1"
    params = []
    if not include_hidden:
        q += " AND l.hidden = 0"
    if user_id:
        q += " AND l.user_id = %s"
        params.append(user_id)
    if target_type:
        q += " AND l.target_type = %s"
        params.append(target_type)
    if target_id:
        q += " AND l.target_id = %s"
        params.append(target_id)
    return get_db().execute(q, params).fetchone()["n"]


def _pct(v):
    """0.04 -> '4%'"""
    try:
        v = float(v)
    except (TypeError, ValueError):
        return escape(str(v))
    s = f"{v*100:.2f}".rstrip("0").rstrip(".")
    return f"{s}%"


def _fmt_g(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return escape(str(v))
    s = f"{v:,.1f}".rstrip("0").rstrip(".")
    return s.replace(",", ".")


def humanize(action, detail_json):
    """Diễn giải nội dung log (JSON kỹ thuật) thành câu tiếng Việt dễ hiểu —
    dùng cho trang Nhật ký thao tác, để người không rành code (sếp) cũng
    đọc được. Trả về chuỗi HTML đã escape phần dữ liệu người dùng nhập,
    an toàn để render với |safe trong template."""
    if not detail_json:
        return ""
    try:
        d = json.loads(detail_json)
    except (ValueError, TypeError):
        return escape(str(detail_json))
    if not isinstance(d, dict):
        return escape(str(d))

    from services.permissions import ROLE_LABELS, PERM_LABELS
    from models.color_version import DUYET_LABELS

    def e(v):
        return escape(str(v))

    def st_label(st):
        return DUYET_LABELS.get(st, st) if st else None

    if action == "TẠO MÀU":
        html = f"Mã màu <b>{e(d.get('ma_mau', ''))}</b>"
        st = st_label(d.get("trang_thai_duyet"))
        if st:
            html += f" — {e(st)}"
        return Markup(html)

    if action == "SỬA CÔNG THỨC":
        cu = d.get("cu") or {}
        moi = d.get("moi") or {}
        lines = []
        for name in moi.keys():
            old_v = cu.get(name, 0) or 0
            new_v = moi.get(name, 0) or 0
            try:
                changed = abs(float(old_v) - float(new_v)) > 1e-9
            except (TypeError, ValueError):
                changed = old_v != new_v
            if changed:
                lines.append(f"{e(name)}: {_pct(old_v)} → {_pct(new_v)}")
        html = "; ".join(lines) if lines else "Không đổi tỷ lệ pigment"
        st = st_label(d.get("trang_thai_duyet"))
        if st:
            html += f" — {e(st)}"
        return Markup(html)

    if action == "TẠO PHIÊN BẢN":
        cu = d.get("cu") or {}
        moi = d.get("moi") or {}
        lines = []
        for name in moi.keys():
            old_v = cu.get(name, 0) or 0
            new_v = moi.get(name, 0) or 0
            try:
                changed = abs(float(old_v) - float(new_v)) > 1e-9
            except (TypeError, ValueError):
                changed = old_v != new_v
            if changed:
                lines.append(f"{e(name)}: {_pct(old_v)} → {_pct(new_v)}")
        html = f"Phiên bản {e(d.get('phien_ban', ''))}"
        html += (": " + "; ".join(lines)) if lines else " (giữ nguyên tỷ lệ)"
        st = st_label(d.get("trang_thai_duyet"))
        if st:
            html += f" — {e(st)}"
        return Markup(html)

    if action == "SỬA PHIÊN BẢN":
        cu = d.get("cu") or {}
        moi = d.get("moi") or {}
        lines = []
        for name in moi.keys():
            old_v = cu.get(name, 0) or 0
            new_v = moi.get(name, 0) or 0
            try:
                changed = abs(float(old_v) - float(new_v)) > 1e-9
            except (TypeError, ValueError):
                changed = old_v != new_v
            if changed:
                lines.append(f"{e(name)}: {_pct(old_v)} → {_pct(new_v)}")
        html = f"Cập nhật phiên bản {e(d.get('phien_ban', ''))}"
        if d.get("ma_mau"):
            html += f" của mã màu <b>{e(d.get('ma_mau'))}</b>"
        if lines:
            html += ": " + "; ".join(lines)
        else:
            html += " (không đổi tỷ lệ pigment)"
        if d.get("gui_lai"):
            html += " — <b>đã gửi lại xin duyệt</b>"
        return Markup(html)

    if action == "DUYỆT PHIÊN BẢN":
        return Markup(f"Đã duyệt phiên bản {e(d.get('phien_ban', ''))} — trở thành bản đang dùng")

    if action == "TỪ CHỐI PHIÊN BẢN":
        ly_do = d.get("ly_do") or ""
        html = f"Từ chối phiên bản {e(d.get('phien_ban', ''))}"
        html += f" — Lý do: {e(ly_do)}" if ly_do else " — không ghi lý do"
        return Markup(html)

    if action == "DÙNG LẠI PHIÊN BẢN":
        return Markup(f"Chuyển sang dùng phiên bản {e(d.get('phien_ban', ''))}")

    if action == "XÓA PHIÊN BẢN":
        return Markup(f"Xóa phiên bản {e(d.get('phien_ban', ''))}")

    if action == "DUYỆT MÀU":
        return Markup(f"Đã duyệt mã màu <b>{e(d.get('ma_mau', ''))}</b>")

    if action == "TỪ CHỐI MÀU":
        ly_do = d.get("ly_do") or ""
        html = f"Từ chối mã màu <b>{e(d.get('ma_mau', ''))}</b>"
        html += f" — Lý do: {e(ly_do)}" if ly_do else " — không ghi lý do"
        return Markup(html)

    if action == "XÓA MÀU":
        return Markup(f"Đã xóa mã màu <b>{e(d.get('ma_mau', ''))}</b>")

    if action == "SỬA MÃ HEX":
        html = f"Đổi mã HEX <b>{e(d.get('cu') or '—')}</b> → <b>{e(d.get('moi', ''))}</b>"
        lab_moi = d.get("lab_moi")
        if lab_moi:
            html += f" — Lab đo máy: L={e(lab_moi[0])} a={e(lab_moi[1])} b={e(lab_moi[2])}"
        return Markup(html)

    if action == "TẢI ẢNH":
        return Markup(f"Tải ảnh — loại: {e(d.get('loai_anh', 'Khác'))}")

    if action == "XÓA ẢNH":
        return Markup("Xóa 1 ảnh")

    if action == "TẠO QR":
        return Markup("Sinh mã QR")

    if action == "THÊM PIGMENT":
        return Markup(f"Thêm pigment '<b>{e(d.get('name', ''))}</b>'")

    if action == "SỬA PIGMENT":
        return Markup(f"Đổi tên pigment '{e(d.get('cu', ''))}' → '{e(d.get('moi', ''))}'")

    if action == "XÓA PIGMENT":
        return Markup(f"Xóa pigment '{e(d.get('name', ''))}'")

    if action == "TẠO PHIẾU CÂN":
        html = f"Tạo phiếu cân mã màu <b>{e(d.get('ma_mau', ''))}</b>"
        if d.get("tong_g") is not None:
            html += f" — tổng {_fmt_g(d['tong_g'])}g"
        if d.get("ty_le_pigment") is not None:
            html += f", tỷ lệ pigment {_pct(d['ty_le_pigment'])}"
        return Markup(html)

    if action == "XUẤT PDF":
        html = f"Xuất PDF phiếu cân mã màu <b>{e(d.get('ma_mau', ''))}</b>"
        if d.get("tong_g") is not None:
            html += f" — {_fmt_g(d['tong_g'])}g"
        return Markup(html)

    if action == "TẠO USER":
        html = f"Tạo tài khoản '<b>{e(d.get('username', ''))}</b>'"
        role = d.get("role")
        if role:
            html += f" — vai trò: {e(ROLE_LABELS.get(role, role))}"
        return Markup(html)

    if action == "SỬA VAI TRÒ":
        role = d.get("role")
        return Markup(f"Đổi vai trò thành <b>{e(ROLE_LABELS.get(role, role))}</b>")

    if action == "SỬA QUYỀN RIÊNG":
        quyen = d.get("quyen") or []
        if not quyen:
            return Markup("Gỡ hết quyền riêng")
        labels = ", ".join(PERM_LABELS.get(p, p) for p in quyen)
        return Markup(f"Cấp quyền riêng: {e(labels)}")

    if action == "ĐẶT LẠI MẬT KHẨU":
        return Markup("Đặt lại mật khẩu")

    if action == "KHÓA TÀI KHOẢN":
        return Markup(f"Khóa tài khoản '<b>{e(d.get('username', ''))}</b>'")

    if action == "MỞ KHÓA TÀI KHOẢN":
        return Markup(f"Mở khóa tài khoản '<b>{e(d.get('username', ''))}</b>'")

    if action == "XÓA USER":
        return Markup(f"Xóa vĩnh viễn tài khoản '<b>{e(d.get('username', ''))}</b>'")

    # Action chưa có trong danh sách xử lý -> hiện thô nhưng gọn, không lỗi
    return escape(json.dumps(d, ensure_ascii=False))