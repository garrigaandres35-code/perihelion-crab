"""
Application Configuration
Manages different configuration environments
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR / "data" / "database.db"}'
    )
    
    # Application settings
    SCRAPING_ENABLED = os.getenv('SCRAPING_ENABLED', 'True') == 'True'
    SCRAPING_INTERVAL = int(os.getenv('SCRAPING_INTERVAL', 3600))
    
    # Paths
    DATA_DIR = BASE_DIR / 'data'
    SCRAPED_DIR = DATA_DIR / 'scraped'
    CONFIG_DIR = BASE_DIR / 'config'
    
    @staticmethod
    def init_app(app):
        """Initialize application configuration"""
        # Create necessary directories
        Config.DATA_DIR.mkdir(exist_ok=True)
        Config.SCRAPED_DIR.mkdir(exist_ok=True)
        Config.CONFIG_DIR.mkdir(exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
