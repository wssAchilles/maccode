"""
GAE 后端服务入口文件
"""

from flask import Flask, jsonify, request
from config import config
from services.firebase_service import FirebaseService
from middleware.cors import configure_cors
from middleware.logging import setup_logging
from utils.exceptions import register_error_handlers
from scheduler import get_scheduler  # 改为导入 get_scheduler，而不是 init_scheduler
import os

# 导入 API 蓝图
from api.auth import auth_bp
from api.data import data_bp
from api.analysis import analysis_bp
from api.history import history_bp
from api.ml import ml_bp
from api.optimization import optimization_bp
from api.rag import rag_bp
from api.dashboard import dashboard_bp
from api.compute_governance import compute_governance_bp, internal_compute_governance_bp
from api.control_tasks import control_tasks_bp, internal_control_tasks_bp
from api.jobs import internal_jobs_bp, jobs_bp
from api.operations import internal_operations_bp, operations_bp
from api.runtime import internal_runtime_bp, runtime_bp


def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    configure_cors(app)
    
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
    app.register_blueprint(ml_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(compute_governance_bp)
    app.register_blueprint(internal_compute_governance_bp)
    app.register_blueprint(control_tasks_bp)
    app.register_blueprint(internal_control_tasks_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(internal_jobs_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(internal_operations_bp)
    app.register_blueprint(runtime_bp)
    app.register_blueprint(internal_runtime_bp)
    get_scheduler(app)
    
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

    def _verify_internal_task_request():
        """Allow internal operational replay without weakening cron-only routes."""
        if app.config.get('DEBUG') or app.config.get('TESTING'):
            return True
        return request.headers.get('X-Internal-Job-Token') == app.config.get('INTERNAL_JOB_TOKEN')

    @app.route('/tasks/fetch-data', methods=['GET'])
    def trigger_fetch_data():
        """数据抓取任务触发器"""
        if not _verify_cron_request():
            return jsonify({'error': 'Unauthorized', 'message': 'Cron header missing'}), 403
            
        try:
            scheduler = get_scheduler(app)
            operation = scheduler.fetch_data_job()  # 手动调用 job 逻辑
            return jsonify({
                'status': 'success',
                'job': 'fetch_data',
                'operation_id': operation.get('job_id') if isinstance(operation, dict) else None,
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/tasks/train-model', methods=['GET'])
    def trigger_train_model():
        """模型训练任务触发器"""
        if not _verify_cron_request():
            return jsonify({'error': 'Unauthorized', 'message': 'Cron header missing'}), 403
            
        try:
            scheduler = get_scheduler(app)
            operation = scheduler.train_model_job()
            return jsonify({
                'status': 'success',
                'job': 'train_model',
                'operation_id': operation.get('job_id') if isinstance(operation, dict) else None,
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/internal/tasks/<task_name>/trigger', methods=['POST'])
    def trigger_internal_task(task_name):
        """Internal replay endpoint for scheduler-backed tasks."""
        if not _verify_internal_task_request():
            return jsonify({'error': 'Unauthorized', 'message': 'Internal job token missing'}), 403

        scheduler = get_scheduler(app)
        task = str(task_name or '').strip().lower()

        try:
            if task == 'fetch_data':
                operation = scheduler.fetch_data_job()
            elif task == 'train_model':
                operation = scheduler.train_model_job()
            else:
                return jsonify({'error': 'Unknown task', 'task': task}), 404

            return jsonify({
                'status': 'accepted',
                'job': task,
                'operation_id': operation.get('job_id') if isinstance(operation, dict) else None,
            }), 202
        except Exception as e:
            return jsonify({'error': str(e), 'task': task}), 500

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
    
    @app.route('/api/health')
    def health():
        return jsonify({
            'status': 'ok',
            'timestamp': os.popen('date -u +\"%Y-%m-%dT%H:%M:%SZ\"').read().strip(),
            'tasks_execution_mode': app.config.get('TASKS_EXECUTION_MODE'),
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
