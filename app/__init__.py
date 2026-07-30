from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app(config_name='development'):
    app = Flask(__name__)
    
    # Configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    # Login manager configuration
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes import main_bp
    from app.distributed_routes import distributed_bp
    from app.rpc_handlers import rpc_bp, init_rpc_handler
    from app.proctoring_routes import proctoring_bp
    from app.fault_tolerance_routes import fault_tolerance_bp
    from app.admin_routes import admin_bp
    from app.blockchain_routes import blockchain_bp
    from app.adaptive_routes import adaptive_bp
    from app.sync_routes import sync_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(distributed_bp)
    app.register_blueprint(rpc_bp)
    app.register_blueprint(proctoring_bp)
    app.register_blueprint(fault_tolerance_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(blockchain_bp)
    app.register_blueprint(adaptive_bp)
    app.register_blueprint(sync_bp)
    
    # Initialize default data
    with app.app_context():
        from app.routes import init_default_data
        init_default_data()
        
        # Create database tables first
        db.create_all()
        
        # Initialize blockchain system
        from app.blockchain_routes import init_blockchain
        init_blockchain()
    
    return app
