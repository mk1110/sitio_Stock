import os
from flask import Flask
from app.extensions import db, login_manager, migrate  # O las extensiones que uses
from config import DevelopmentConfig, ProductionConfig

def create_app():
    app = Flask(__name__)

    # Detecta automáticamente si está en Railway (si existe la variable de base de datos)
    if os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL'):
        app.config.from_object(ProductionConfig)
    else:
        app.config.from_object(DevelopmentConfig)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Registrar Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.products import products_bp
    from app.blueprints.reports import reports_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.tasks import tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tasks_bp)

    return app