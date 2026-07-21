"""Hệ thống phân quyền.

4 role cố định: admin, quan_ly, san_xuat, khach_hang.
Mỗi role có một tập quyền mặc định (ROLE_DEFAULTS).

Ngoài ra, một số user (chủ yếu là "khách hàng đặc biệt") có thể được
CẤP THÊM một số quyền riêng qua bảng user_permissions — nhưng chỉ giới hạn
trong GRANTABLE_EXTRA (tao_mau, tao_pigment). Quyền sửa/xóa/duyệt/xem nhật ký/
quản lý người dùng/xuất PDF KHÔNG BAO GIỜ được cấp cho vai trò khách hàng,
bất kể override gì — chặn cứng ở NEVER_FOR_KHACH_HANG để tránh cấu hình sai.
"""

ROLE_ADMIN = "admin"
ROLE_QUAN_LY = "quan_ly"
ROLE_SAN_XUAT = "san_xuat"
ROLE_KHACH_HANG = "khach_hang"

ROLES = [ROLE_ADMIN, ROLE_QUAN_LY, ROLE_SAN_XUAT, ROLE_KHACH_HANG]

ROLE_LABELS = {
    ROLE_ADMIN: "Admin",
    ROLE_QUAN_LY: "Quản lý",
    ROLE_SAN_XUAT: "Sản xuất",
    ROLE_KHACH_HANG: "Khách hàng",
}

# Quyền mặc định theo từng role
ROLE_DEFAULTS = {
    ROLE_ADMIN: {
        "xem_mau", "tao_mau", "sua_mau", "duyet_mau",
        "tao_pigment", "sua_pigment", "xoa_pigment",
        "tao_phieu_can", "xuat_pdf", "upload_anh", "xem_qr", "tao_qr",
        "xem_nhat_ky", "quan_ly_nguoi_dung", "quan_ly_anh",
    },
    ROLE_QUAN_LY: {
        "xem_mau", "tao_mau", "sua_mau", "duyet_mau",
        "tao_pigment", "sua_pigment", "xoa_pigment",
        "tao_phieu_can", "xuat_pdf", "upload_anh", "xem_qr", "tao_qr",
        "xem_nhat_ky",
    },
    ROLE_SAN_XUAT: {
        "xem_mau", "tao_mau", "sua_mau",
        "tao_phieu_can", "xuat_pdf", "upload_anh", "xem_qr", "tao_qr",
    },
    ROLE_KHACH_HANG: {
        "xem_mau", "tao_phieu_can", "xem_qr",
    },
}

# Quyền được phép cấp thêm riêng cho từng user (vd. khách hàng đặc biệt)
GRANTABLE_EXTRA = {"tao_mau", "tao_pigment"}

PERM_LABELS = {
    "xem_mau": "Xem thư viện & chi tiết màu",
    "tao_mau": "Tạo màu mới",
    "sua_mau": "Sửa công thức màu",
    "duyet_mau": "Duyệt / từ chối công thức",
    "tao_pigment": "Tạo pigment mới",
    "sua_pigment": "Sửa tên pigment",
    "xoa_pigment": "Xóa pigment",
    "tao_phieu_can": "Tạo & xem phiếu cân",
    "xuat_pdf": "In / xuất PDF phiếu cân",
    "upload_anh": "Tải ảnh lên",
    "xem_qr": "Xem mã QR",
    "tao_qr": "Sinh mã QR",
    "xem_nhat_ky": "Xem nhật ký thao tác",
    "quan_ly_nguoi_dung": "Quản lý người dùng",
    "quan_ly_anh": "Thư viện ảnh (xem/xóa toàn bộ ảnh hệ thống)",
}

# Quyền không bao giờ được có ở vai trò khách hàng, dù cấp thêm kiểu gì
NEVER_FOR_KHACH_HANG = {
    "sua_mau", "duyet_mau", "sua_pigment", "xoa_pigment",
    "xuat_pdf", "xem_nhat_ky", "quan_ly_nguoi_dung",
}


def effective_permissions(user, extra_grants=None):
    """user: Row từ bảng users (cần có cột 'role').
    extra_grants: set các quyền được cấp thêm riêng (từ models.permission.list_for_user),
    hoặc None nếu chỉ muốn xem quyền mặc định theo role."""
    role = user["role"] if user else None
    perms = set(ROLE_DEFAULTS.get(role, set()))
    if extra_grants:
        allowed_extra = extra_grants & GRANTABLE_EXTRA
        if role == ROLE_KHACH_HANG:
            allowed_extra -= NEVER_FOR_KHACH_HANG  # chặn cứng, phòng hờ cấu hình sai
        perms |= allowed_extra
    return perms


def has_permission(user, permission, extra_grants=None):
    return permission in effective_permissions(user, extra_grants)