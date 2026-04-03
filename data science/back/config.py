"""
后端配置文件
包含 Firebase、GCP、Flask 等配置
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置类"""
    
    # Flask 配置
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # GCP 配置
    GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'data-science-44398')
    GCP_REGION = os.getenv('GCP_REGION', 'asia-northeast1')
    
    # Firebase 配置
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', GCP_PROJECT_ID)
    # Firestore database id defaults to the primary database, not the storage bucket.
    FIRESTORE_DATABASE = os.getenv('FIRESTORE_DATABASE', '(default)')
    
    # Cloud Storage 配置
    STORAGE_BUCKET_NAME = os.getenv('STORAGE_BUCKET_NAME', 'data-science-44398.firebasestorage.app')
    HEAVY_SERVICE_URL = os.getenv('HEAVY_SERVICE_URL', '')

    # 任务系统配置
    JOBS_COLLECTION = os.getenv('JOBS_COLLECTION', 'jobs')
    CONTROL_TASKS_COLLECTION = os.getenv('CONTROL_TASKS_COLLECTION', 'control_tasks')
    ACTIVITY_COLLECTION = os.getenv('ACTIVITY_COLLECTION', 'activity')
    TASKS_EXECUTION_MODE = os.getenv(
        'TASKS_EXECUTION_MODE',
        'inline' if DEBUG else 'cloud_tasks',
    ).lower()
    TASKS_QUEUE_NAME = os.getenv('TASKS_QUEUE_NAME', 'industrial-jobs')
    TASKS_LOCATION = os.getenv('TASKS_LOCATION', GCP_REGION)
    TASKS_MAX_ATTEMPTS = int(os.getenv('TASKS_MAX_ATTEMPTS', '3'))
    INTERNAL_BASE_URL = os.getenv('INTERNAL_BASE_URL', 'http://localhost:8080')
    INTERNAL_JOB_TOKEN = os.getenv('INTERNAL_JOB_TOKEN', 'dev-internal-job-token')
    RATE_LIMIT_BACKEND = os.getenv(
        'RATE_LIMIT_BACKEND',
        'memory' if DEBUG else 'firestore',
    ).lower()

    # 优化业务配置
    BATTERY_CONFIG = {
        'capacity': float(os.getenv('DEFAULT_BATTERY_CAPACITY', 100.0)),
        'max_power': float(os.getenv('DEFAULT_BATTERY_POWER', 40.0)),
        'efficiency': float(os.getenv('DEFAULT_BATTERY_EFFICIENCY', 0.95)),
    }

    # 电价配置 (单一事实来源)
    PRICE_SCHEDULE = {
        'valley': 0.3,
        'normal': 0.6,
        'peak': 1.0,
        'valley_hours_list': [0, 1, 2, 3, 4, 5, 6, 7, 22, 23],
        'normal_hours_list': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],
        'peak_hours_list': [18, 19, 20, 21],
        'valley_desc': '00:00-08:00, 22:00-24:00',
        'normal_desc': '08:00-18:00',
        'peak_desc': '18:00-22:00',
        'currency': '元/kWh'
    }
    
    # CORS 配置 (生产级别 - 严格限制)
    CORS_ORIGINS = [
        'https://data-science-44398.web.app',        # Firebase Hosting 生产环境
        'https://data-science-44398.firebaseapp.com', # Firebase Hosting 备用域名
    ]
    
    # CORS 详细配置
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    
    # API 配置
    API_VERSION = 'v1'
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TASKS_EXECUTION_MODE = 'inline'
    RATE_LIMIT_BACKEND = 'memory'
    
    # 开发环境允许 localhost
    CORS_ORIGINS = Config.CORS_ORIGINS + [
        'http://localhost:*',
        'http://127.0.0.1:*',
    ]


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    RATE_LIMIT_BACKEND = 'firestore'


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    TASKS_EXECUTION_MODE = 'inline'
    RATE_LIMIT_BACKEND = 'memory'
    WTF_CSRF_ENABLED = False



# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
