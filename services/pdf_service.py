"""Xuất phiếu cân ra PDF bằng reportlab (dễ cài trên Windows hơn WeasyPrint).
Tự tìm font TTF hỗ trợ tiếng Việt trên máy."""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors as rl_colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle)
from reportlab.lib.styles import ParagraphStyle
import config

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/times.ttf", "C:/Windows/Fonts/timesbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf",
     "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]

FONT, FONT_BOLD = "Helvetica", "Helvetica-Bold"
for regular, bold in _FONT_CANDIDATES:
    if Path(regular).exists():
        try:
            pdfmetrics.registerFont(TTFont("VNFont", regular))
            FONT = "VNFont"
            if Path(bold).exists():
                pdfmetrics.registerFont(TTFont("VNFont-Bold", bold))
                FONT_BOLD = "VNFont-Bold"
            else:
                FONT_BOLD = "VNFont"
            break
        except Exception:
            continue


def _fmt_g(v):
    return f"{v:,.1f}".rstrip("0").rstrip(".").replace(",", ".")


def export_weighing_sheet(info, calc, color):
    """info: dict {created_at, nguoi_tao}, calc: kết quả calculator, color: Row colors.
    Trả về đường dẫn tuyệt đối của file PDF."""
    import time
    config.PDF_FOLDER.mkdir(parents=True, exist_ok=True)
    filename = f"phieu_can_{color['id']}_{int(time.time())}.pdf"
    filepath = config.PDF_FOLDER / filename

    title = ParagraphStyle("title", fontName=FONT_BOLD, fontSize=15, spaceAfter=4)
    normal = ParagraphStyle("normal", fontName=FONT, fontSize=10.5, leading=15)
    bold = ParagraphStyle("bold", fontName=FONT_BOLD, fontSize=10.5, leading=15)

    doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                            leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=16*mm, bottomMargin=16*mm)
    story = [
        Paragraph("BRICON – PHIẾU CÂN MÀU SẢN XUẤT", title),
        Paragraph(f"Ngày tạo: {info['created_at']}", normal),
        Paragraph(f"Người tạo: {info['nguoi_tao']}", normal),
        Spacer(1, 6),
        Paragraph(f"Mã màu: <b>{color['ma_mau']}</b> &nbsp;&nbsp;|&nbsp;&nbsp; Tên màu: {color['ten_mau'] or '—'}", normal),
        Paragraph(
            f"Tổng thành phẩm: <b>{_fmt_g(calc['tong_thanh_pham_g'])} g</b>"
            f" &nbsp;&nbsp;|&nbsp;&nbsp; Tỷ lệ pigment: <b>{calc['ty_le_pigment']*100:.2f}%</b>", normal),
        Spacer(1, 10),
    ]

    data = [["STT", "NGUYÊN LIỆU CẦN CÂN", "TỶ LỆ THÀNH PHẨM", "KHỐI LƯỢNG (g)"]]
    for l in calc["lines"]:
        data.append([str(l["stt"]), l["ten"],
                     f"{l['ty_le_thanh_pham']*100:.3f}%", _fmt_g(l["khoi_luong_g"])])
    data.append(["", "TỔNG CỘNG", "", _fmt_g(calc["tong_can"])])

    table = Table(data, colWidths=[14*mm, 78*mm, 42*mm, 40*mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -2), FONT),
        ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#e8e8e8")),
        ("GRID", (0, 0), (-1, -1), 0.6, rl_colors.HexColor("#555555")),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(table)

    check = "KHỚP" if calc["khop"] else "CÓ CHÊNH LỆCH – KIỂM TRA LẠI"
    story += [
        Spacer(1, 8),
        Paragraph(f"Kiểm tra tổng: <b>{check}</b> (chênh lệch {_fmt_g(abs(calc['chenh_lech']))} g)", normal),
        Spacer(1, 28),
    ]

    sign = Table([
        [Paragraph("NGƯỜI CÂN", bold), Paragraph("NGƯỜI KIỂM TRA", bold)],
        [Paragraph("(Ký, ghi rõ họ tên)", normal), Paragraph("(Ký, ghi rõ họ tên)", normal)],
        ["", ""],
    ], colWidths=[87*mm, 87*mm], rowHeights=[8*mm, 6*mm, 28*mm])
    sign.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(sign)

    doc.build(story)
    return filepath
