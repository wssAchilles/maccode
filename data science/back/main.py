"""
GAE 后端服务入口文件
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from config import config
from services.firebase_service import FirebaseService
from middleware.logging import setup_logging
from utils.exceptions import register_error_handlers
from scheduler import get_scheduler  # 改为导入 get_scheduler，而不是 init_scheduler
import os

# 导入 API 蓝图
from api.auth import auth_bp
from api.data import data_bp
from api.analysis import analysis_bp
from api.history import history_bp
# from api.ml import ml_bp  # 暂时禁用
from api.optimization import optimization_bp


def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    CORS(app, 
         origins=app.config['CORS_ORIGINS'],
         supports_credentials=app.config.get('CORS_SUPPORTS_CREDENTIALS', True),
         allow_headers=app.config.get('CORS_ALLOW_HEADERS', ['Content-Type', 'Authorization']),
         methods=app.config.get('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']))
    
    setup_logging(app)
    register_error_handlers(app)
    
    try:
        FirebaseService.initialize(project_id=app.config['GCP_PROJECT_ID'])
    except Exception as e:
        print(f"⚠️ Firebase 初始化失败: {e}")
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(optimization_bp)
    
    # ---------------------------------------------------------
    # ❌ 移除/注释掉原来的 init_scheduler() 调用
    # ---------------------------------------------------------
    # try:
    #     scheduler = init_scheduler()
    #     ...
    # except ...
    
    # ---------------------------------------------------------
    # ✅ 新增: GAE Cron 触发路由
    # ---------------------------------------------------------
    
    def _verify_cron_request():
        """验证请求是否来自 GAE Cron Service"""
        # 在本地开发环境跳过检查
        if os.getenv('FLASK_ENV') == 'development':
            return True
        # GAE 会自动添加此 Header，外部无法伪造
        return request.headers.get('X-Appengine-Cron') == 'true'

    @app.route('/tasks/fetch-data', methods=['GET'])
    def trigger_fetch_data():
        """数据抓取任务触发器"""
        if not _verify_cron_request():
            return jsonify({'error': 'Unauthorized', 'message': 'Cron header missing'}), 403
            
        try:
            scheduler = get_scheduler()
            scheduler.fetch_data_job()  # 手动调用 job 逻辑
            return jsonify({'status': 'success', 'job': 'fetch_data'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/tasks/train-model', methods=['GET'])
    def trigger_train_model():
        """模型训练任务触发器"""
        if not _verify_cron_request():
            return jsonify({'error': 'Unauthorized', 'message': 'Cron header missing'}), 403
            
        try:
            scheduler = get_scheduler()
            scheduler.train_model_job()
            return jsonify({'status': 'success', 'job': 'train_model'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/tasks/status', methods=['GET'])
    def get_task_status():
        """
        获取定时任务执行状态（用于监控）
        
        Query Parameters:
            - task: 任务名称 (fetch_data 或 train_model)，可选
            - limit: 返回数量，默认 10
        """
        try:
            from services.task_monitor import get_task_monitor
            
            monitor = get_task_monitor()
            task_name = request.args.get('task')
            limit = int(request.args.get('limit', 10))
            
            executions = monitor.get_recent_executions(task_name, limit)
            
            # 获取统计信息
            stats = {}
            for name in ['fetch_data', 'train_model']:
                stats[name] = monitor.get_task_stats(name, days=7)
            
            return jsonify({
                'success': True,
                'recent_executions': executions,
                'stats': stats
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # ---------------------------------------------------------

    @app.route('/')
    def index():
        return jsonify({
            'message': 'Data Science API Server',
            'version': app.config['API_VERSION'],
            'status': 'running'
        })
    
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'ok',
            'timestamp': os.popen('date -u +"%Y-%m-%dT%H:%M:%SZ"').read().strip()
        })
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': {'code': 'NOT_FOUND', 'message': 'Resource not found'}}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({'error': {'code': 'INTERNAL_ERROR', 'message': 'Internal server error'}}), 500
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)