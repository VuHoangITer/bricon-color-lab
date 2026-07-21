import math
from models import get_db

TOLERANCE = 0.0001  # giống công thức Excel ABS(K-1) < 0.0001


def status_of(total, has_any):
    """Trạng thái tổng tỷ lệ pigment của 1 phiên bản (giống cột L Excel).
    KHÔNG liên quan tới trạng thái duyệt — đó là chuyện của color_version."""
    if not has_any:
        return "CHƯA KHAI BÁO"
    return "ĐẠT" if abs(total - 1.0) < TOLERANCE else "SAI TỔNG"


def create(ma_mau, ten_mau, ghi_chu, user_id, hex_color=None):
    """Tạo MÀU (chỉ thông tin chung: mã, tên, ghi chú, HEX).
    Công thức/tỷ lệ pigment là chuyện của color_version.create_version(),
    gọi riêng ngay sau khi có color_id."""
    db = get_db()
    cur = db.execute(
        "INSERT INTO colors (ma_mau, ten_mau, ghi_chu, created_by, hex_color) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (ma_mau.strip(), ten_mau.strip(), (ghi_chu or "").strip(), user_id, hex_color),
    )
    color_id = cur.fetchone()["id"]
    db.commit()
    return color_id


def update_info(color_id, ma_mau, ten_mau, ghi_chu, hex_color=None):
    """Sửa thông tin chung của màu (mã/tên/ghi chú/HEX) — KHÔNG đụng công
    thức/phiên bản. Sửa công thức phải qua color_version.create_version()."""
    db = get_db()
    db.execute(
        """UPDATE colors SET ma_mau=%s, ten_mau=%s, ghi_chu=%s, hex_color=%s,
           updated_at=CURRENT_TIMESTAMP WHERE id=%s""",
        (ma_mau.strip(), ten_mau.strip(), (ghi_chu or "").strip(), hex_color, color_id),
    )
    db.commit()


def get(color_id):
    return get_db().execute("SELECT * FROM colors WHERE id = %s", (color_id,)).fetchone()


def next_ma_mau():
    """Gợi ý mã màu tiếp theo dựa trên mã màu thuần số lớn nhất hiện có
    (vd: đang có 1..30 -> gợi ý '31'). Bỏ qua mã có ký tự khác chữ số
    (vd: 'BR-000138'). Người dùng vẫn sửa được nếu không ưng.
    Dùng cho NỘI BỘ (admin/quản lý/sản xuất) — mã màu chính thức của công
    ty, không tái sử dụng số đã xóa (an toàn hơn cho hàng thật ngoài xưởng)."""
    row = get_db().execute(
        """SELECT MAX(CAST(ma_mau AS INTEGER)) AS max_num FROM colors
           WHERE ma_mau ~ '^[0-9]+$'"""
    ).fetchone()
    max_num = row["max_num"] if row and row["max_num"] is not None else 0
    return str(max_num + 1)


def next_ma_mau_khach_hang(username):
    """Gợi ý mã màu riêng cho TÀI KHOẢN KHÁCH HÀNG — dạng KH-{username}-NN,
    tách hẳn khỏi dãy số nội bộ của công ty (next_ma_mau) để không lẫn lộn
    màu khách tự tạo với mã màu chính thức. Đánh số riêng theo từng khách
    (mỗi khách có dãy NN của riêng mình, bắt đầu từ 01)."""
    prefix = f"KH-{username}-"
    # Escape ký tự đặc biệt của LIKE ('%', '_') có trong username, phòng khi
    # username chứa những ký tự đó — tránh khớp nhầm mã màu của khách khác.
    like_pattern = prefix.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_") + "%"
    rows = get_db().execute(
        "SELECT ma_mau FROM colors WHERE ma_mau LIKE %s", (like_pattern,)
    ).fetchall()
    max_num = 0
    for r in rows:
        suffix = r["ma_mau"][len(prefix):]
        if suffix.isdigit():
            max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:02d}"


def _active_ratio_summary(color_row):
    """Tính total/status từ phiên bản ĐANG DÙNG của 1 màu (dùng nội bộ cho
    list_all()). color_row cần có cột active_version_id (từ JOIN)."""
    db = get_db()
    if not color_row["active_version_id"]:
        return 0.0, "CHƯA CÓ BẢN DÙNG"
    rows = db.execute(
        """SELECT cvp.ty_le FROM color_version_pigments cvp
           WHERE cvp.version_id = %s""",
        (color_row["active_version_id"],),
    ).fetchall()
    total = sum(r["ty_le"] for r in rows)
    has_any = any(r["ty_le"] > 0 for r in rows)
    return total, status_of(total, has_any) if rows else "CHƯA CÓ BẢN DÙNG"


def list_all():
    """Danh sách màu kèm trạng thái phiên bản ĐANG DÙNG — CHỈ hiện màu đang
    có 1 phiên bản active (đã được duyệt). Màu chưa có bản nào được duyệt
    thì không hiện trong thư viện chung (xem ở trang Chờ duyệt / Của tôi)."""
    db = get_db()
    rows = db.execute(
        """SELECT c.*, cv.id AS active_version_id, cv.version_number AS active_version_number
           FROM colors c
           JOIN color_versions cv ON cv.color_id = c.id AND cv.is_active = 1
           ORDER BY c.id"""
    ).fetchall()
    result = []
    for c in rows:
        total, status = _active_ratio_summary(c)
        result.append({
            "color": c,
            "total": total,
            "status": status,
            "active_version_number": c["active_version_number"],
        })
    return result


def is_ready_for_weighing(color_id):
    """True nếu màu có 1 phiên bản đang dùng và tổng pigment ĐẠT 100%."""
    from models import color_version as cv_model
    active = cv_model.get_active(color_id)
    if not active:
        return False
    d = cv_model.detail(active["id"])
    return d is not None and d["status"] == "ĐẠT"


def set_qr_path(color_id, path):
    db = get_db()
    db.execute("UPDATE colors SET qr_code_path=%s WHERE id=%s", (path, color_id))
    db.commit()


def _hex_to_rgb(hex_color):
    if not hex_color:
        return None
    v = hex_color.lstrip("#")
    if len(v) != 6:
        return None
    try:
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _srgb_to_linear(c):
    """1 kênh màu sRGB (0-255) -> giá trị linear (0-1), bước bắt buộc trước
    khi đổi sang không gian XYZ/Lab (giải mã gamma sRGB chuẩn)."""
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_xyz(rgb):
    """RGB (0-255) -> XYZ, theo ma trận chuẩn sRGB / D65."""
    r, g, b = (_srgb_to_linear(v) for v in rgb)
    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041
    return x * 100, y * 100, z * 100


# Điểm trắng tham chiếu D65 — chuẩn cho màn hình/sRGB
_D65 = (95.0489, 100.0, 108.8840)


def _xyz_to_lab(xyz):
    """XYZ -> Lab (CIE L*a*b*), so với điểm trắng D65."""
    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)
    fx, fy, fz = (f(v / w) for v, w in zip(xyz, _D65))
    L = (116 * fy) - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return L, a, b


def _hex_to_lab(hex_color):
    rgb = _hex_to_rgb(hex_color)
    if not rgb:
        return None
    return _xyz_to_lab(_rgb_to_xyz(rgb))


def _delta_e2000(lab1, lab2):
    """CIEDE2000 — công thức chuẩn ngành (sơn/in ấn/dệt) để đo độ khác biệt
    màu THEO CẢM NHẬN MẮT NGƯỜI trên không gian Lab. Chính xác hơn nhiều so
    với đo khoảng cách thô trên RGB, đặc biệt ở vùng màu sáng/pastel."""
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    C_bar7 = ((C1 + C2) / 2) ** 7
    G = 0.5 * (1 - math.sqrt(C_bar7 / (C_bar7 + 25 ** 7)))

    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)

    def hue(ap, b):
        return 0.0 if ap == 0 and b == 0 else math.degrees(math.atan2(b, ap)) % 360

    h1p, h2p = hue(a1p, b1), hue(a2p, b2)

    delta_Lp = L2 - L1
    delta_Cp = C2p - C1p

    if C1p * C2p == 0:
        delta_hp = 0.0
    else:
        dh = h2p - h1p
        if dh > 180:
            dh -= 360
        elif dh < -180:
            dh += 360
        delta_hp = dh
    delta_Hp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(delta_hp) / 2)

    L_bar_p = (L1 + L2) / 2
    C_bar_p = (C1p + C2p) / 2

    if C1p * C2p == 0:
        h_bar_p = h1p + h2p
    elif abs(h1p - h2p) > 180:
        h_bar_p = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    else:
        h_bar_p = (h1p + h2p) / 2

    T = (1 - 0.17 * math.cos(math.radians(h_bar_p - 30))
         + 0.24 * math.cos(math.radians(2 * h_bar_p))
         + 0.32 * math.cos(math.radians(3 * h_bar_p + 6))
         - 0.20 * math.cos(math.radians(4 * h_bar_p - 63)))

    delta_theta = 30 * math.exp(-(((h_bar_p - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(C_bar_p ** 7 / (C_bar_p ** 7 + 25 ** 7))

    Sl = 1 + (0.015 * (L_bar_p - 50) ** 2) / math.sqrt(20 + (L_bar_p - 50) ** 2)
    Sc = 1 + 0.045 * C_bar_p
    Sh = 1 + 0.015 * C_bar_p * T
    Rt = -math.sin(math.radians(2 * delta_theta)) * Rc

    return math.sqrt(
        (delta_Lp / Sl) ** 2
        + (delta_Cp / Sc) ** 2
        + (delta_Hp / Sh) ** 2
        + Rt * (delta_Cp / Sc) * (delta_Hp / Sh)
    )


# Quy ΔE00 ra % "giống nhau" bằng suy giảm hàm mũ (không phải chia tuyến tính
# cho 1 mốc cố định như redmean cũ — cách đó khiến các màu sáng/pastel luôn
# bị đẩy lên 85-99% dù khác tông rõ). Hằng số 14.43 chọn sao cho khớp các
# mốc ΔE00 chuẩn ngành: ΔE00 ≈ 1 (mắt tinh mới phân biệt được) -> ~93%,
# ΔE00 ≈ 2 (ranh giới "nhìn ra khác") -> ~87%, ΔE00 ≈ 10 (khác rõ) -> ~50%.
_DELTA_E_SCALE = 14.43


def _similarity_pct(delta_e):
    pct = 100 * math.exp(-delta_e / _DELTA_E_SCALE)
    return max(0, min(100, round(pct)))


def find_similar(hex_color, exclude_id=None, limit=8):
    """Tìm các màu có mã HEX gần giống nhất — chỉ so với màu đang có phiên
    bản active (tức đang hiện trong thư viện) và đã khai báo hex_color.
    So màu bằng CIEDE2000 trên không gian Lab (chuẩn ngành, theo cảm nhận
    mắt người), không phải khoảng cách thô trên RGB.
    Trả về list [{"color":..., "distance":..., "similarity_pct":...}],
    sắp xếp gần giống nhất trước (distance ở đây là ΔE00, càng nhỏ càng giống)."""
    target_lab = _hex_to_lab(hex_color)
    if not target_lab:
        return []
    db = get_db()
    rows = db.execute(
        """SELECT c.* FROM colors c
           JOIN color_versions cv ON cv.color_id = c.id AND cv.is_active = 1
           WHERE c.hex_color IS NOT NULL AND c.hex_color != ''"""
    ).fetchall()
    results = []
    for c in rows:
        if exclude_id and c["id"] == exclude_id:
            continue
        lab = _hex_to_lab(c["hex_color"])
        if not lab:
            continue
        delta_e = _delta_e2000(target_lab, lab)
        results.append({"color": c, "distance": delta_e, "similarity_pct": _similarity_pct(delta_e)})
    results.sort(key=lambda r: r["distance"])
    return results[:limit]


def delete(color_id):
    """Xóa hẳn màu. color_versions (và color_version_pigments, color_images
    theo sau) tự xóa theo (ON DELETE CASCADE). activity_logs KHÔNG bị xóa
    theo — giữ lại lịch sử màu từng tồn tại."""
    db = get_db()
    db.execute("DELETE FROM colors WHERE id = %s", (color_id,))
    db.commit()