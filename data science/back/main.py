"""
GAE 后端服务入口文件

此文件包含:
- Flask 应用初始化
- 路由注册
- 中间件配置
- 错误处理
- Firebase Admin SDK 初始化
"""

from flask import Flask, jsonify
from flask_cors import CORS
from config import config
from services.firebase_service import FirebaseService
from middleware.logging import setup_logging
from utils.exceptions import register_error_handlers
import os

# 导入 API 蓝图
from api.auth import auth_bp
from api.data import data_bp
from api.analysis import analysis_bp
from api.history import history_bp
# from api.ml import ml_bp  # 暂时禁用，MLService 未实现
from api.optimization import optimization_bp


def create_app(config_name=None):
    """
    应用工厂函数
    
    Args:
        config_name: 配置名称 ('development' 或 'production')
        
    Returns:
        Flask: Flask 应用实例
    """
    # 创建 Flask 应用
    app = Flask(__name__)
    
    # 加载配置
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 配置 CORS
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True),
         allow_headers=app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization']),
         methods=app.config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']))
    
    # 设置日志中间件
    setup_logging(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 初始化 Firebase Admin SDK
    try:
        FirebaseService.initialize(project_id=app.config['GCP_PROJECT_ID'])
    except Exception as e:
        print(f"⚠️ Firebase 初始化失败: {e}")
        # 不抛出异常，允许应用继续运行（某些路由可能不需要 Firebase）
    
    # 注册蓝图 (API 路由)
    app.register_blueprint(auth_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(history_bp)
    # app.register_blueprint(ml_bp)  # 暂时禁用
    app.register_blueprint(optimization_bp)
    
    # 根路由
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Data Science API Server',
            'version': app.config['API_VERSION'],
            'status': 'running'
        })
    
    # 健康检查
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'ok',
            'timestamp': os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
        })
    
    # 全局错误处理
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'error': {
                'code': 'NOT_FOUND',
                'message': 'Resource not found'
            }
        }), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'Internal server error'
            }
        }), 500
    
    return app


# 创建应用实例 (GAE 需要名为 'app' 的变量)
app = create_app()


if __name__ == '__main__':
    # 本地开发模式
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
