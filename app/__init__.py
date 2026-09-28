from flask import Flask
from config import DevelopmentConfig
from app.extensions import db, login_manager

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar las extensiones vinculándolas a la app
    db.init_app(app)
    login_manager.init_app(app)

    # Registro de Blueprints
    from app.blueprints.auth.routes import auth_bp
    from app.blueprints.products.routes import products_bp
    from app.blueprints.admin.routes import admin_bp
    from app.blueprints.reports.routes import reports_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    return app