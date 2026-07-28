import io
import base64
import qrcode


def generate_data_uri(text):
    """Sinh QR chứa TRỰC TIẾP nội dung text (không phải link tới trang nào) —
    trả về data URI base64, nhúng thẳng vào HTML bằng <img src="...">, KHÔNG
    lưu file ra đĩa. Dùng cho phiếu cân — vì phiếu cân là stateless (không
    lưu lịch sử vào DB), nên không có trang cố định nào để link tới; QR
    phải tự chứa đủ thông tin để đọc được ngay cả khi không có mạng/app."""
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"