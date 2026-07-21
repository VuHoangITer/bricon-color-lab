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

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)