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
    
    # Cloud Storage 配置
    STORAGE_BUCKET_NAME = os.getenv('STORAGE_BUCKET_NAME', 'data-science-44398.firebasestorage.app')
    
    # CORS 配置 (生产级别 - 严格限制)
    CORS_ORIGINS = [
        'https://data-science-44398.web.app',        # Firebase Hosting 生产环境
        'https://data-science-44398.firebaseapp.com', # Firebase Hosting 备用域名
    ]
    
    # API 配置
    API_VERSION = 'v1'
    
    @staticmethod
    def init_app(app):
        """初始化应用配置"""
        pass


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
    # 开发环境允许 localhost
    CORS_ORIGINS = Config.CORS_ORIGINS + [
        'http://localhost:*',
        'http://127.0.0.1:*',
    ]


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
