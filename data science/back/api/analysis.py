"""
数据分析 API 路由
处理用户上传的数据文件并进行分析
"""

from flask import Blueprint, jsonify, request
from services.firebase_service import require_auth
from services.analysis_pipeline_service import AnalysisPipelineService
from services.drift_service import DriftService
from utils.exceptions import ValidationError
from utils.responses import error_response, success_response
from middleware.rate_limit import rate_limit
import logging

logger = logging.getLogger(__name__)

analysis_bp = Blueprint('analysis', __name__, url_prefix='/api/analysis')


@analysis_bp.route('/analyze-csv', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=20, window_seconds=60)
@require_auth
def analyze_csv():
    """
    分析 CSV 文件
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          - storage_path: GCS 文件路径
          - filename: (可选) 文件名
    
    响应:
        {
            "success": true,
            "analysis_result": {...}
        }
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json()
        
        if not data or 'storage_path' not in data:
            raise ValidationError('缺少参数：storage_path')
            
        response = AnalysisPipelineService.run_csv_analysis(
            uid=uid,
            storage_path=data['storage_path'],
            filename=data.get('filename'),
            save_to_storage=data.get('save_to_storage', True),
        )
        return success_response(response)
        
    except ValidationError as e:
        logger.warning(f"验证错误: {str(e)}")
        return error_response('VALIDATION_ERROR', str(e), status_code=400)
    except Exception as e:
        logger.error(f"分析失败: {str(e)}", exc_info=True)
        return error_response('ANALYSIS_ERROR', f'分析过程出错: {str(e)}', status_code=500)


@analysis_bp.route('/analyze-excel', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=20, window_seconds=60)
@require_auth
def analyze_excel():
    """
    分析 Excel 文件
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          - storage_path: GCS 文件路径
          - filename: (可选) 文件名
          - sheet_name: (可选) 工作表名称
    
    响应:
        与 analyze-csv 相同的格式
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json()
        
        if not data or 'storage_path' not in data:
            raise ValidationError('缺少参数：storage_path')
            
        storage_path = data['storage_path']
        filename = data.get('filename', storage_path.split('/')[-1])
        sheet_name = data.get('sheet_name')
        
        logger.info(f"[{uid}] 收到 Excel 分析请求: {storage_path}")
        
        # 从 Cloud Storage 下载文件
        storage = StorageService()
        
        if not storage.file_exists(storage_path):
            raise ValidationError('文件不存在')
            
        file_bytes = storage.download_file(storage_path)
        file_stream = io.BytesIO(file_bytes)
        
        # 验证文件大小
        file_size = len(file_bytes)
        if not validate_file_size(file_size, max_size_mb=50):
            raise ValidationError('文件大小不能超过 50MB')
        
        logger.info(f"[{uid}] 开始分析 Excel 文件: {filename}")
        
        # 执行分析
        analysis_result = AnalysisService.analyze_excel(file_stream, filename, uid, sheet_name)
        
        if not analysis_result.get('success'):
            return jsonify(analysis_result), 400
        
        response = {
            'success': True,
            'analysis_result': analysis_result,
            'message': '分析完成',
            'storage_path': storage_path
        }
        
        logger.info(f"[{uid}] Excel 分析完成")
        
        return jsonify(response), 200
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.error(f"分析失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'ANALYSIS_ERROR',
            'message': f'分析过程出错: {str(e)}'
        }), 500


@analysis_bp.route('/supported-formats', methods=['GET'])
def supported_formats():
    """
    获取支持的文件格式列表
    
    无需认证的公开端点
    """
    return jsonify({
        'success': True,
        'formats': {
            'csv': {
                'extensions': ['.csv'],
                'mime_types': ['text/csv'],
                'max_size_mb': 50
            },
            'excel': {
                'extensions': ['.xlsx', '.xls'],
                'mime_types': [
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.ms-excel'
                ],
                'max_size_mb': 50
            }
        }
    }), 200


@analysis_bp.route('/drift/detect', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=10, window_seconds=60)
@require_auth
def detect_drift():
    """
    检测数据漂移 (PSI/KL)
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
        
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        reference_path = data.get('reference_path')
        current_path = data.get('current_path')
        features = data.get('features') # list of strings
        
        if not reference_path or not current_path or not features:
            raise ValidationError("缺少参数: reference_path, current_path, features")
            
        logger.info(f"[{uid}] 开始漂移检测")
        
        storage = StorageService()
        
        # 加载数据
        ref_bytes = storage.download_file(reference_path)
        cur_bytes = storage.download_file(current_path)
        
        ref_df = pd.read_csv(io.BytesIO(ref_bytes))
        cur_df = pd.read_csv(io.BytesIO(cur_bytes))
        
        drift_service = DriftService()
        
        # 计算漂移
        drift_results = drift_service.detect_drift(ref_df, cur_df, features)
        
        # 生成报告
        report = drift_service.generate_drift_report(drift_results)
        
        return jsonify({
            'success': True,
            'drift_results': drift_results,
            'report': report
        }), 200
        
    except Exception as e:
        logger.error(f"漂移检测失败: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'SERVER_ERROR', 'message': str(e)}), 500
