from flask import Flask, render_template
import config
import models
from models.schema import db
from flask_migrate import Migrate
from routes import register_blueprints


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    # Cấu hình cho Flask-SQLAlchemy/Flask-Migrate — CHỈ dùng để quản lý
    # schema (flask db migrate / flask db upgrade). Toàn bộ truy vấn thực
    # tế của app vẫn đi qua models.get_db() (psycopg2 thô) như cũ, không
    # đổi gì ở đó.
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql+psycopg2://{config.DB_USER}:{config.DB_PASSWORD}"
        f"@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    Migrate(app, db)

    models.init_app(app)
    register_blueprints(app)

    @app.template_filter("pct")
    def pct(v, digits=2):
        """0.095 -> '9.5%'"""
        s = f"{v*100:.{digits}f}".rstrip("0").rstrip(".")
        return f"{s}%"

    @app.template_filter("gram")
    def gram(v):
        s = f"{v:,.1f}".rstrip("0").rstrip(".")
        return s.replace(",", ".")

    @app.template_filter("file_kind")
    def file_kind(path_or_name):
        """'anh1.jpg' -> 'image' | 'clip.mp4' -> 'video' | còn lại -> 'other'
        (dùng để chọn cách hiển thị trong thư viện: <img>, <video>, hay thẻ file)."""
        name = str(path_or_name or "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext in config.IMAGE_EXT:
            return "image"
        if ext in config.VIDEO_EXT:
            return "video"
        return "other"

    @app.template_filter("file_icon")
    def file_icon(path_or_name):
        """Icon cho file KHÔNG phải ảnh/video (docx, pdf, xlsx, zip...)."""
        name = str(path_or_name or "")
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        return {
            "pdf": "📕",
            "doc": "📄", "docx": "📄",
            "xls": "📊", "xlsx": "📊", "csv": "📊",
            "ppt": "📙", "pptx": "📙",
            "zip": "🗄", "rar": "🗄", "7z": "🗄",
        }.get(ext, "📎")

    @app.template_filter("file_name")
    def file_name(path):
        return str(path or "").rsplit("/", 1)[-1]

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)