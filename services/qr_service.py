import qrcode
import config


def generate_for_color(color_id):
    """Tạo QR chứa link trang chi tiết màu, trả về đường dẫn tương đối trong /static."""
    url = f"{config.BASE_URL}/colors/{color_id}"
    img = qrcode.make(url)
    config.QR_FOLDER.mkdir(parents=True, exist_ok=True)
    filename = f"color_{color_id}.png"
    img.save(config.QR_FOLDER / filename)
    return f"uploads/qr/{filename}"
