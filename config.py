import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration - support both MySQL and SQLite
    DB_TYPE = os.environ.get('DB_TYPE', 'mysql')  # 'mysql' or 'sqlite'
    
    if DB_TYPE == 'mysql':
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or (
            f"mysql+pymysql://{os.environ.get('DB_USER', 'root')}:"
            f"{os.environ.get('DB_PASSWORD', '')}@"
            f"{os.environ.get('DB_HOST', 'localhost')}:"
            f"{os.environ.get('DB_PORT', '3306')}/"
            f"{os.environ.get('DB_NAME', 'exam_system')}"
        )
    else:
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///exam_system.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
class DevelopmentConfig(Config):
    DEBUG = True
    DB_TYPE = 'sqlite'  # Use SQLite for development by default
    
class ProductionConfig(Config):
    DEBUG = False
    DB_TYPE = 'mysql'  # Use MySQL for production
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
