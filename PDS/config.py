"""Application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    
    # Application settings
    WORKING_HOURS_PER_DAY = int(os.environ.get('WORKING_HOURS_PER_DAY', 8))
    GRACE_PERIOD_MINUTES = int(os.environ.get('GRACE_PERIOD_MINUTES', 15))
    
    # Demo admin credentials (used by seed script only)
    DEMO_ADMIN_EMAIL = os.environ.get('DEMO_ADMIN_EMAIL', 'admin@company.com')
    DEMO_ADMIN_PASSWORD = os.environ.get('DEMO_ADMIN_PASSWORD', 'Admin@123')
    
    # Pagination
    ITEMS_PER_PAGE = 15
    
    # Upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
