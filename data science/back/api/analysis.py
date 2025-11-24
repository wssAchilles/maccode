"""
数据分析 API 路由
处理用户上传的数据文件并进行分析
"""

from flask import Blueprint, jsonify, request
from services.firebase_service import require_auth
from services.analysis_service import AnalysisService
from services.storage_service import StorageService
from services.history_service import HistoryService
from utils.exceptions import ValidationError
from utils.validators import validate_file_type, validate_file_size
from middleware.rate_limit import rate_limit
import logging
import io
import pandas as pd
import time

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
            
        storage_path = data['storage_path']
        filename = data.get('filename', storage_path.split('/')[-1])
        
        logger.info(f"[{uid}] 收到 CSV 分析请求: {storage_path}")
        
        # 从 Cloud Storage 下载文件
        storage = StorageService()
        
        # 验证文件是否存在
        if not storage.file_exists(storage_path):
            raise ValidationError('文件不存在')
            
        file_bytes = storage.download_file(storage_path)
        file_stream = io.BytesIO(file_bytes)
        
        # 验证文件大小 (这里已经是下载后的，其实可以在前端限制，或者检查 blob metadata)
        file_size = len(file_bytes)
        if not validate_file_size(file_size, max_size_mb=50):
            raise ValidationError('文件大小不能超过 50MB')
            
        logger.info(f"[{uid}] 开始分析文件: {filename} ({file_size} bytes)")
        
        start_time = time.time()
        
        # 读取 DataFrame 一次（避免重复读取）
        df = pd.read_csv(file_stream)
        load_time = time.time() - start_time
        logger.info(f"[{uid}] 数据加载耗时: {load_time:.2f}s, 数据形状: {df.shape}")
        
        # 执行基础分析（直接使用已加载的 DataFrame）
        basic_start = time.time()
        basic_result = AnalysisService.analyze_dataframe(df, filename, uid)
        basic_time = time.time() - basic_start
        logger.info(f"[{uid}] 基础分析耗时: {basic_time:.2f}s")
        
        if not basic_result.get('success'):
            return jsonify(basic_result), 400
        
        # 执行质量检查（容错处理）
        quality_analysis = {}
        try:
            quality_start = time.time()
            quality_result = AnalysisService.perform_quality_check(df)
            quality_time = time.time() - quality_start
            logger.info(f"[{uid}] 质量检查耗时: {quality_time:.2f}s")
            
            if quality_result.get('success'):
                quality_analysis = quality_result
            else:
                quality_analysis = {
                    'success': False,
                    'error': quality_result.get('error', 'UNKNOWN'),
                    'message': quality_result.get('message', '质量检查失败')
                }
        except Exception as e:
            logger.warning(f"[{uid}] 质量检查失败: {str(e)}")
            quality_analysis = {
                'success': False,
                'error': 'QUALITY_CHECK_ERROR',
                'message': f'质量检查失败: {str(e)}'
            }
        
        # 执行相关性分析（容错处理）
        correlations = {}
        try:
            corr_start = time.time()
            corr_result = AnalysisService.calculate_correlations(df)
            corr_time = time.time() - corr_start
            logger.info(f"[{uid}] 相关性分析耗时: {corr_time:.2f}s")
            
            if corr_result.get('success'):
                correlations = corr_result
            else:
                correlations = {
                    'success': False,
                    'error': corr_result.get('error', 'UNKNOWN'),
                    'message': corr_result.get('message', '相关性分析失败')
                }
        except Exception as e:
            logger.warning(f"[{uid}] 相关性分析失败: {str(e)}")
            correlations = {
                'success': False,
                'error': 'CORRELATION_ERROR',
                'message': f'相关性分析失败: {str(e)}'
            }
        
        # 执行统计检验（容错处理）
        statistical_tests = {}
        try:
            stat_start = time.time()
            stat_result = AnalysisService.perform_statistical_tests(df)
            stat_time = time.time() - stat_start
            logger.info(f"[{uid}] 统计检验耗时: {stat_time:.2f}s")
            
            if stat_result.get('success'):
                statistical_tests = stat_result
            else:
                statistical_tests = {
                    'success': False,
                    'error': stat_result.get('error', 'UNKNOWN'),
                    'message': stat_result.get('message', '统计检验失败')
                }
        except Exception as e:
            logger.warning(f"[{uid}] 统计检验失败: {str(e)}")
            statistical_tests = {
                'success': False,
                'error': 'STATISTICAL_TEST_ERROR',
                'message': f'统计检验失败: {str(e)}'
            }
        
        total_time = time.time() - start_time
        logger.info(f"[{uid}] CSV 分析完成，总耗时: {total_time:.2f}s")
        
        # 重构响应结构
        # 构建分析结果
        analysis_result = {
            'basic_info': basic_result.get('basic_info', {}),
            'preview': basic_result.get('preview', []),
            'descriptive_statistics': basic_result.get('descriptive_statistics', {}),
            'missing_data': basic_result.get('missing_data', {}),
            'type_distribution': basic_result.get('type_distribution', {}),
            'correlation_matrix': basic_result.get('correlation_matrix'),
            'quality_analysis': quality_analysis,
            'correlations': correlations,
            'statistical_tests': statistical_tests
        }
        
        # 保存历史记录到 Firestore
        try:
            # 构建 Cloud Storage 文件 URL
            storage_url = f"gs://{storage.bucket_name}/{storage_path}"
            
            # 异步保存历史记录（不阻塞响应）
            record_id = HistoryService.save_analysis_record(
                uid=uid,
                filename=filename,
                storage_url=storage_url,
                analysis_result=analysis_result
            )
            
            if record_id:
                logger.info(f"[{uid}] 分析记录已保存: {record_id}")
            else:
                logger.warning(f"[{uid}] 分析记录保存失败")
        except Exception as e:
            # 历史记录保存失败不影响响应
            logger.error(f"[{uid}] 保存历史记录失败: {str(e)}")
        
        # 构建响应
        response = {
            'success': True,
            'analysis_result': analysis_result,
            'message': '分析完成',
            'storage_path': storage_path,
            'performance': {
                'load_time': round(load_time, 2),
                'basic_analysis_time': round(basic_time, 2),
                'total_time': round(total_time, 2)
            }
        }
        
        return jsonify(response), 200
        
    except ValidationError as e:
        logger.warning(f"验证错误: {str(e)}")
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
