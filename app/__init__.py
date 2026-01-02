"""
Flask Application Factory
Creates and configures the Flask application instance
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'

def configure_logging(app):
    """Configure logging to file and console"""
    import logging
    from logging.handlers import RotatingFileHandler
    
    # Create logs directory if not exists
    if not os.path.exists('logs'):
        os.mkdir('logs')
        
    # File handler
    # Aumentado a 5MB para evitar rotación excesiva
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Add to root logger only (to capture all module logs via propagation)
    # Check if a FileHandler already exists to prevent duplication on reloads
    root_logger = logging.getLogger()
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    
    # Ensure app.logger propagates to root (this is default but explicit is better)
    app.logger.propagate = True
    
    # Remove any existing handlers from app.logger to avoid double logging
    for h in app.logger.handlers[:]:
        app.logger.removeHandler(h)
    
    # Silence werkzeug access logs (GET /api/scraping/process-logs etc.)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('Perihelion Crab startup')

def create_app(config_name=None):
    """
    Application factory pattern
    Creates and configures the Flask application
    """
    app = Flask(__name__)
    
    # Configure logging first
    configure_logging(app)
    
    # Load configuration
    from app.config import config
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize app configuration (create directories)
    config[config_name].init_app(app)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    
    # User loader for Flask-Login
    from app.models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.scraping import scraping_bp
    from app.routes.api import api_bp
    from app.routes.auth import auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(scraping_bp, url_prefix='/api/scraping')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Create database tables
    with app.app_context():
        db.create_all()
        # Create default profiles if they don't exist
        _create_default_profiles()
    
    # Register custom template filters
    from app.utils.menu import get_menu_items
    
    @app.context_processor
    def inject_menu():
        """Inject menu items into all templates"""
        return dict(menu_items=get_menu_items())
    
    return app


def _create_default_profiles():
    """Create default user profiles if they don't exist"""
    from app.models import Profile
    
    default_profiles = [
        {'name': 'admin', 'description': 'Acceso completo al sistema', 'permissions': {'all': True}},
        {'name': 'analyst', 'description': 'Visualización y análisis de datos', 'permissions': {'read': True, 'analyze': True}},
        {'name': 'viewer', 'description': 'Solo lectura', 'permissions': {'read': True}},
    ]
    
    for profile_data in default_profiles:
        existing = Profile.query.filter_by(name=profile_data['name']).first()
        if not existing:
            profile = Profile(**profile_data)
            db.session.add(profile)
    
    db.session.commit()
