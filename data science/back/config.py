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
    # This project runs Firestore in Datastore compatibility mode on a named database.
    FIRESTORE_DATABASE = os.getenv('FIRESTORE_DATABASE', 'my-datasci-project-bucket')
    
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
    ORCHESTRATOR_BASE_URL = os.getenv('ORCHESTRATOR_BASE_URL', '')
    INTERNAL_JOB_TOKEN = os.getenv('INTERNAL_JOB_TOKEN', 'dev-internal-job-token')
    ORCHESTRATOR_REQUEST_TIMEOUT_S = float(os.getenv('ORCHESTRATOR_REQUEST_TIMEOUT_S', '10'))
    ORCHESTRATOR_MAX_LIGHT_PARALLEL = int(os.getenv('ORCHESTRATOR_MAX_LIGHT_PARALLEL', '4'))
    ORCHESTRATOR_MAX_HEAVY_PARALLEL = int(os.getenv('ORCHESTRATOR_MAX_HEAVY_PARALLEL', '2'))
    ORCHESTRATOR_DISPATCH_TIMEOUT_S = int(os.getenv('ORCHESTRATOR_DISPATCH_TIMEOUT_S', '1800'))
    RATE_LIMIT_BACKEND = os.getenv(
        'RATE_LIMIT_BACKEND',
        'memory' if DEBUG else 'firestore',
    ).lower()
    COMPUTE_ACCELERATION_COLLECTION = os.getenv(
        'COMPUTE_ACCELERATION_COLLECTION',
        'compute_acceleration',
    )
    COMPUTE_GOVERNANCE_COLLECTION = os.getenv(
        'COMPUTE_GOVERNANCE_COLLECTION',
        'runtime_governance',
    )
    COMPUTE_PROFILE_ENABLED = os.getenv('COMPUTE_PROFILE_ENABLED', 'true').lower() == 'true'
    COMPUTE_PROFILE_WINDOW = int(os.getenv('COMPUTE_PROFILE_WINDOW', '24'))
    COMPUTE_FEATURE_WARNING_MS = float(os.getenv('COMPUTE_FEATURE_WARNING_MS', '200'))
    COMPUTE_SCENARIO_WARNING_MS = float(os.getenv('COMPUTE_SCENARIO_WARNING_MS', '450'))
    COMPUTE_NATIVE_ENABLED = os.getenv('COMPUTE_NATIVE_ENABLED', 'false').lower() == 'true'
    COMPUTE_NATIVE_MODULE = os.getenv('COMPUTE_NATIVE_MODULE', 'rolling_features_native')
    COMPUTE_NATIVE_GUARD_ENABLED = os.getenv(
        'COMPUTE_NATIVE_GUARD_ENABLED',
        'true',
    ).lower() == 'true'
    COMPUTE_NATIVE_GUARD_FAILURE_THRESHOLD = int(
        os.getenv('COMPUTE_NATIVE_GUARD_FAILURE_THRESHOLD', '3'),
    )
    COMPUTE_NATIVE_GUARD_WINDOW_MINUTES = int(
        os.getenv('COMPUTE_NATIVE_GUARD_WINDOW_MINUTES', '30'),
    )
    COMPUTE_FEATURE_NATIVE_MIN_SPEEDUP = float(
        os.getenv('COMPUTE_FEATURE_NATIVE_MIN_SPEEDUP', '1.15'),
    )
    COMPUTE_SCENARIO_VECTOR_MIN_SPEEDUP = float(
        os.getenv('COMPUTE_SCENARIO_VECTOR_MIN_SPEEDUP', '1.05'),
    )
    COMPUTE_STATUS_WINDOW = int(os.getenv('COMPUTE_STATUS_WINDOW', '5'))
    COMPUTE_BENCHMARK_STALE_HOURS = int(
        os.getenv('COMPUTE_BENCHMARK_STALE_HOURS', '168'),
    )
    RAG_BACKEND_MODE = os.getenv('RAG_BACKEND_MODE', 'storage_fallback').lower()
    ML_TRAIN_BACKEND_DEFAULT = os.getenv(
        'ML_TRAIN_BACKEND_DEFAULT',
        'cloud_run_legacy',
    ).strip().lower()
    ML_TRAIN_VERTEX_ENABLED = os.getenv(
        'ML_TRAIN_VERTEX_ENABLED',
        'false',
    ).lower() == 'true'
    ML_TRAIN_VERTEX_ROLLOUT_MODE = os.getenv(
        'ML_TRAIN_VERTEX_ROLLOUT_MODE',
        'disabled',
    ).strip().lower()
    ML_TRAIN_VERTEX_WHITELIST_UIDS = tuple(
        item.strip()
        for item in os.getenv('ML_TRAIN_VERTEX_WHITELIST_UIDS', '').split(',')
        if item.strip()
    )
    ML_TRAIN_VERTEX_MIN_FILE_SIZE_BYTES = int(
        os.getenv('ML_TRAIN_VERTEX_MIN_FILE_SIZE_BYTES', '0'),
    )
    ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS = int(
        os.getenv('ML_TRAIN_VERTEX_MAX_PARALLEL_JOBS', '2'),
    )
    ML_TRAIN_VERTEX_MAX_RUNTIME_S = int(
        os.getenv('ML_TRAIN_VERTEX_MAX_RUNTIME_S', '7200'),
    )
    ML_TRAIN_VERTEX_CPU_ONLY = os.getenv(
        'ML_TRAIN_VERTEX_CPU_ONLY',
        'true',
    ).lower() == 'true'
    ML_TRAIN_VERTEX_RECONCILE_DELAY_S = int(
        os.getenv('ML_TRAIN_VERTEX_RECONCILE_DELAY_S', '30'),
    )
    VERTEX_REGION = os.getenv('VERTEX_REGION', 'us-central1').strip()
    VERTEX_TRAINING_IMAGE_URI = os.getenv('VERTEX_TRAINING_IMAGE_URI', '').strip()
    VERTEX_TRAINING_STAGING_BUCKET = os.getenv(
        'VERTEX_TRAINING_STAGING_BUCKET',
        '',
    ).strip()
    VERTEX_TRAINING_SERVICE_ACCOUNT = os.getenv(
        'VERTEX_TRAINING_SERVICE_ACCOUNT',
        '',
    ).strip()
    VERTEX_TRAINING_MACHINE_TYPE = os.getenv(
        'VERTEX_TRAINING_MACHINE_TYPE',
        'n1-standard-4',
    ).strip()
    VERTEX_TRAINING_ACCELERATOR_TYPE = os.getenv(
        'VERTEX_TRAINING_ACCELERATOR_TYPE',
        '',
    ).strip()
    VERTEX_TRAINING_ACCELERATOR_COUNT = int(
        os.getenv('VERTEX_TRAINING_ACCELERATOR_COUNT', '0'),
    )
    TRAINING_CALLBACK_BASE_URL = os.getenv(
        'TRAINING_CALLBACK_BASE_URL',
        INTERNAL_BASE_URL,
    ).strip()

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
    CORS_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
    
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
