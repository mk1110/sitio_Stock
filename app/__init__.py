import os
import logging
import time

from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db, login_manager, migrate  # O las extensiones que uses
from config import DevelopmentConfig, ProductionConfig


def ensure_schema(app, intentos=2):
    """
    Crea las tablas que falten en la base de datos al arrancar la aplicación.

    En producción las migraciones las aplica la fase `release:` del Procfile
    (`flask db upgrade`). Si esa fase falla, no se ejecuta, o el despliegue se
    hace antes de que la base esté disponible, la app igual levanta pero las
    páginas que dependen de tablas nuevas devuelven 500.

    Por eso, antes de devolver la app lista, se verifica el esquema y se
    completa de forma idempotente. Es una red de seguridad: la vía principal
    sigue siendo Alembic.

    Nunca hace fallar el arranque. Si la base no está accesible, se registra el
    aviso y la app sigue levantando (el login, por ejemplo, mostró el problema
    real de configuración de conexión).
    """
    for intento in range(intentos):
        try:
            with app.app_context():
                existentes = set(db.inspect(db.engine).get_table_names())
                faltantes = [t for t in db.metadata.tables if t not in existentes]

                if not faltantes:
                    return  # El esquema ya estaba completo

                app.logger.warning(
                    'Esquema incompleto: faltan las tablas %s. Creándolas...',
                    ', '.join(sorted(faltantes))
                )
                db.create_all()
                app.logger.info('Esquema completado. Ejecutá `flask db upgrade` para versionarlo.')
                return

        except SQLAlchemyError:
            # Varios workers de gunicorn pueden intentar crearlas al mismo tiempo.
            # Si eso pasa, el segundo intento ya encuentra las tablas creadas.
            app.logger.warning(
                'No se pudo verificar el esquema (intento %d/%d).',
                intento + 1, intentos, exc_info=True
            )
            if intento + 1 < intentos:
                time.sleep(2)

        except Exception:
            app.logger.exception('Error inesperado al verificar el esquema de la base de datos.')
            return


def create_app():
    app = Flask(__name__)
    logging.basicConfig(level=logging.INFO)

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

    # El esquema debe existir antes de que entre el primer request
    ensure_schema(app)

    return app
