from routes.auth import bp as auth_bp
from routes.colors import bp as colors_bp
from routes.weighing import bp as weighing_bp
from routes.logs import bp as logs_bp
from routes.pigments import bp as pigments_bp
from routes.users import bp as users_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(colors_bp)
    app.register_blueprint(weighing_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(pigments_bp)
    app.register_blueprint(users_bp)
