import os

class BaseConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'clave-secreta-desarrollo')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:password@localhost/stock_db'

class ProductionConfig(BaseConfig):
    DEBUG = False
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')
    
    if db_url and db_url.startswith("mysql://"):
        db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
        
    SQLALCHEMY_DATABASE_URI = db_url

# Para importar Config directamente si fuera necesario
Config = ProductionConfig