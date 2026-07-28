"""Thư viện file lưu trữ (admin-only) — quét TRỰC TIẾP 3 thư mục trên đĩa
(static/uploads/images, qr, pdf), không dựa vào bảng DB làm nguồn chính.
Lý do: đây là công cụ để admin xem "thực tế đang có gì trên đĩa" mà không
cần SSH vào VPS — quét đĩa còn lộ ra được file "mồ côi" (có file nhưng
không còn được DB track, hoặc ngược lại) mà cách dựa vào DB không thấy được.
"""
import re
from datetime import datetime
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import config
from models import get_db
from models import image as image_model
from models import color as color_model
from models.activity_log import log
from routes.auth import permission_required

bp = Blueprint("images", __name__)

PER_PAGE = 48


def _page_range(page, total_pages, window=2):
    """Danh sách số trang rút gọn kiểu [1, '…', 4, 5, 6, '…', 20]."""
    pages = {1, total_pages}
    for p in range(page - window, page + window + 1):
        if 1 <= p <= total_pages:
            pages.add(p)
    ordered = sorted(pages)
    result, prev = [], None
    for p in ordered:
        if prev is not None and p - prev > 1:
            result.append("…")
        result.append(p)
        prev = p
    return result


def _fmt_size(num_bytes):
    n = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _paginate(items, page, per_page):
    total = len(items)
    total_pages = max(1, -(-total // per_page))  # ceil division
    page = min(max(1, page), total_pages)
    start = (page - 1) * per_page
    return items[start:start + per_page], page, total_pages, total


# ---------- Tab Ảnh ----------

def _list_image_files():
    folder = config.IMAGE_FOLDER
    if not folder.exists():
        return []
    db_rows = {}
    for row in get_db().execute(
        """SELECT ci.file_path, ci.loai_anh, ci.ghi_chu, c.ma_mau, c.ten_mau
           FROM color_images ci JOIN colors c ON c.id = ci.color_id"""
    ).fetchall():
        db_rows[Path(row["file_path"]).name] = row

    files = []
    for p in folder.iterdir():
        if not p.is_file():
            continue
        stat = p.stat()
        db_row = db_rows.get(p.name)
        m = re.match(r"^color(\d+)_", p.name)
        color_id = int(m.group(1)) if m else None
        ma_mau = db_row["ma_mau"] if db_row else None
        if ma_mau is None and color_id:
            c = color_model.get(color_id)
            ma_mau = c["ma_mau"] if c else None
        files.append({
            "name": p.name,
            "size": _fmt_size(stat.st_size),
            "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "mtime_sort": stat.st_mtime,
            "color_id": color_id,
            "ma_mau": ma_mau,
            "loai_anh": db_row["loai_anh"] if db_row else None,
            "tracked": db_row is not None,
        })
    files.sort(key=lambda f: f["mtime_sort"], reverse=True)
    return files


@bp.route("/anh")
@permission_required("quan_ly_anh")
def index():
    f_color = (request.args.get("ma_mau") or "").strip() or None
    only_orphan = request.args.get("orphan") == "1"

    files = _list_image_files()
    if f_color:
        files = [f for f in files if f["ma_mau"] == f_color]
    if only_orphan:
        files = [f for f in files if not f["tracked"]]

    page = request.args.get("page", 1, type=int) or 1
    page_files, page, total_pages, total = _paginate(files, page, PER_PAGE)

    return render_template("images/list.html", files=page_files,
                           f_color=f_color, only_orphan=only_orphan,
                           page=page, total_pages=total_pages, total=total,
                           page_range=_page_range(page, total_pages), active_tab="anh")


@bp.route("/anh/delete", methods=["POST"])
@permission_required("quan_ly_anh")
def delete():
    filename = Path(request.form.get("filename") or "").name
    if not filename:
        flash("Tên file không hợp lệ.", "error")
        return redirect(url_for("images.index"))
    rel_path = f"uploads/images/{filename}"
    image_model.delete_by_path(rel_path)
    try:
        (config.IMAGE_FOLDER / filename).unlink(missing_ok=True)
    except Exception:
        pass
    log(session["user_id"], "XÓA ẢNH", None, None, {"file": filename})
    flash(f"Đã xóa ảnh '{filename}'.", "success")
    return redirect(url_for("images.index", page=request.args.get("page", type=int)))



# ---------- Tab PDF ----------

def _list_pdf_files():
    folder = config.PDF_FOLDER
    if not folder.exists():
        return []
    files = []
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() == ".pdf":
            stat = p.stat()
            ma_mau = None
            parts = p.stem.split("_")
            if len(parts) >= 3 and parts[0] == "phieu" and parts[1] == "can" and parts[2].isdigit():
                c = color_model.get(int(parts[2]))
                ma_mau = c["ma_mau"] if c else None
            files.append({
                "name": p.name,
                "size_bytes": stat.st_size,
                "size": _fmt_size(stat.st_size),
                "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "mtime_sort": stat.st_mtime,
                "ma_mau": ma_mau,
            })
    files.sort(key=lambda f: f["mtime_sort"], reverse=True)
    return files


@bp.route("/anh/pdf")
@permission_required("quan_ly_anh")
def pdf_list():
    files = _list_pdf_files()
    total_size = sum(f["size_bytes"] for f in files)
    return render_template("images/pdf_list.html", files=files,
                           total_count=len(files), total_size=_fmt_size(total_size), active_tab="pdf")


@bp.route("/anh/pdf/delete", methods=["POST"])
@permission_required("quan_ly_anh")
def pdf_delete():
    filename = Path(request.form.get("filename") or "").name
    if not filename.lower().endswith(".pdf"):
        flash("Tên file không hợp lệ.", "error")
        return redirect(url_for("images.pdf_list"))
    try:
        (config.PDF_FOLDER / filename).unlink(missing_ok=True)
        log(session["user_id"], "XÓA PDF", None, None, {"file": filename})
        flash(f"Đã xóa file '{filename}'.", "success")
    except Exception as e:
        flash(f"Lỗi khi xóa file: {e}", "error")
    return redirect(url_for("images.pdf_list"))