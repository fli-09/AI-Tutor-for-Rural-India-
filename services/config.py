import os
from typing import Dict, Any

class Config:
    """Application configuration"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'ai_tutor_rural_india_secret_key_2024')
    DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = '../uploads'
    AUDIO_FOLDER = '../audio'
    
    # Database settings
    DB_PATH = '../progress.json'
    
    # LLM settings
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL = 'gemini-2.0-flash-exp'
    
    # Voice settings
    DEFAULT_LANGUAGE = 'en'
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'hi': 'Hindi',
        'ta': 'Tamil',
        'te': 'Telugu',
        'bn': 'Bengali',
        'mr': 'Marathi',
        'gu': 'Gujarati',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'pa': 'Punjabi'
    }
    
    # Quiz settings
    DEFAULT_QUESTIONS_COUNT = 5
    MAX_QUESTIONS_COUNT = 20
    QUIZ_TIME_LIMIT = 1800  # 30 minutes in seconds
    
    # Offline mode settings
    OFFLINE_MODE = os.environ.get('OFFLINE_MODE', 'False').lower() == 'true'
    
    # Development settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """Get LLM configuration"""
        return {
            'api_key': cls.GEMINI_API_KEY,
            'model': cls.GEMINI_MODEL,
            'offline_mode': cls.OFFLINE_MODE
        }
    
    @classmethod
    def get_voice_config(cls) -> Dict[str, Any]:
        """Get voice configuration"""
        return {
            'default_language': cls.DEFAULT_LANGUAGE,
            'supported_languages': cls.SUPPORTED_LANGUAGES,
            'offline_mode': cls.OFFLINE_MODE
        }
    
    @classmethod
    def get_quiz_config(cls) -> Dict[str, Any]:
        """Get quiz configuration"""
        return {
            'default_questions': cls.DEFAULT_QUESTIONS_COUNT,
            'max_questions': cls.MAX_QUESTIONS_COUNT,
            'time_limit': cls.QUIZ_TIME_LIMIT
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    OFFLINE_MODE = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    OFFLINE_MODE = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    OFFLINE_MODE = True

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 