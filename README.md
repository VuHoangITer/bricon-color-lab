# BRICON COLOR LAB — MVP local

Web app thay thế file Excel `FILE_CÂN_MÀU_MỞ_RỘNG.xlsx` (thư viện màu + phiếu cân),
kèm 5 chức năng bổ sung: đăng nhập, QR, upload ảnh, xuất PDF, nhật ký thao tác.

## Cài đặt & chạy

```bash
pip install -r requirements.txt
python seed.py        # tạo database.db + nạp 8 pigment, 30 màu từ Excel
python app.py         # mở http://localhost:5000
```

Tài khoản mặc định: **admin / admin123** (đổi trong DB trước khi dùng thật).
Cấu hình trong `.env` (SECRET_KEY, BASE_URL, PORT...).

## Ghi chú

- Màu 7, 8 seed cố tình sai tổng (99% / 103%) — để test badge SAI TỔNG.
- Màu 3, 4 giữ ghi chú "BOSS BÁO CÔNG THỨC ĐANG LỆCH" từ file gốc.
- 30 màu seed chưa có QR — vào chi tiết màu bấm "Sinh mã QR". Màu tạo mới tự có QR.
- PDF dùng reportlab, tự tìm font tiếng Việt trên máy (Arial trên Windows).
- Logic tính cân nằm ở `services/calculator.py` — cùng công thức với tab PHIẾU CÂN V4.
- Sau này chuyển PostgreSQL: sửa `models/__init__.py` (kết nối + schema), các model dùng SQL chuẩn nên đổi ít.
