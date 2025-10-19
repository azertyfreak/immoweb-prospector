import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Database
    DATABASE_NAME = os.environ.get('DATABASE_NAME') or 'immoweb_data.db'
    
    # Email Settings
    EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', '0') == '1'
    EMAIL_FROM = os.environ.get('EMAIL_FROM', '')
    EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
    EMAIL_TO = os.environ.get('EMAIL_TO', '')
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '465'))
    
    # Scraping Settings
    CHECK_INTERVAL = int(os.environ.get('CHECK_INTERVAL', '60'))
    MAX_RESULTS_PER_SEARCH = int(os.environ.get('MAX_RESULTS_PER_SEARCH', '20'))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', '10'))
    
    # Rate Limiting
    SCRAPE_DELAY = int(os.environ.get('SCRAPE_DELAY', '2'))
    
    @staticmethod
    def init_app(app):
        """Initialize application with configuration"""
        pass
