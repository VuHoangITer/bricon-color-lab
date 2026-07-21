"""Logic tính phiếu cân — bản Python của tab PHIẾU CÂN V4.

Công thức gốc trong Excel:
    Tổng pigment (g)  = Tổng thành phẩm × Tỷ lệ pigment          (E5 = B6*B7)
    Base (g)          = Tổng thành phẩm × (1 - Tỷ lệ pigment)    (E4 = B6*(1-B7))
    KL từng pigment   = Tổng pigment × tỷ lệ chuẩn hóa           (N = E5*M)
    Tỷ lệ chuẩn hóa   = ty_le / tổng ty_le                       (M = K/L)
"""


def calculate(tong_thanh_pham_g, ty_le_pigment, pigment_rows):
    """pigment_rows: list các dict/Row có 'name' và 'ty_le'.
    Trả về dict đầy đủ để render phiếu cân."""
    tong_pigment_g = tong_thanh_pham_g * ty_le_pigment
    base_g = tong_thanh_pham_g * (1 - ty_le_pigment)

    tong_ct = sum(r["ty_le"] for r in pigment_rows)  # cột L trong Excel

    lines = [{
        "stt": 1,
        "ten": "BASE THÀNH PHẦN A",
        "ty_le_thanh_pham": 1 - ty_le_pigment,
        "khoi_luong_g": base_g,
    }]
    stt = 2
    for r in pigment_rows:
        if r["ty_le"] <= 0:
            continue
        chuan_hoa = r["ty_le"] / tong_ct if tong_ct > 0 else 0
        lines.append({
            "stt": stt,
            "ten": r["name"],
            "ty_le_thanh_pham": chuan_hoa * ty_le_pigment,
            "khoi_luong_g": tong_pigment_g * chuan_hoa,
        })
        stt += 1

    tong_can = sum(l["khoi_luong_g"] for l in lines)
    chenh_lech = tong_can - tong_thanh_pham_g
    return {
        "tong_thanh_pham_g": tong_thanh_pham_g,
        "ty_le_pigment": ty_le_pigment,
        "base_g": base_g,
        "tong_pigment_g": tong_pigment_g,
        "tong_ct": tong_ct,
        "lines": lines,
        "tong_can": tong_can,
        "chenh_lech": chenh_lech,
        "khop": abs(chenh_lech) < 0.01,
    }
