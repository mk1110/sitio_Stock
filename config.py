import os

class Config:
    # Clave secreta para cookies/sesiones (en producción la toma de Railway)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-segura-mariano-12345')

    # Detección y formato de la URL de base de datos para Railway
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')

    if db_url and db_url.startswith("mysql://"):
        # Transforma mysql:// a mysql+pymysql:// para SQLAlchemy
        db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

    # Si no hay variable de entorno, usa el MySQL local de desarrollo
    SQLALCHEMY_DATABASE_URI = db_url or 'mysql+pymysql://root:password@localhost/stock_db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False