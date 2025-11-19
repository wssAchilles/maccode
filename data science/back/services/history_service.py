"""
历史记录服务
负责将分析记录存储到 Cloud Firestore
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

logger = logging.getLogger(__name__)


class HistoryService:
    """历史记录服务类"""
    
    @staticmethod
    def _get_firestore_client():
        """获取 Firestore 客户端，使用 Native Mode 数据库"""
        try:
            # 使用 google-cloud-firestore 直接访问指定数据库
            # 而不是通过 firebase-admin（它不支持多数据库）
            return firestore.Client(database='my-datasci-project-bucket')
        except Exception as e:
            logger.error(f"Failed to get Firestore client: {e}")
            raise
    
    @staticmethod
    def _prepare_analysis_summary(analysis_result: Dict) -> Dict:
        """准备分析摘要，移除大字段以避免超过 Firestore 1MB 限制"""
        summary = {}
        
        # 保留基本信息
        if 'basic_info' in analysis_result:
            summary['basic_info'] = analysis_result['basic_info']
        
        # 保留质量分析（但移除详细的异常值索引）
        if 'quality_analysis' in analysis_result:
            quality = analysis_result['quality_analysis'].copy()
            
            if 'outlier_detection' in quality:
                outlier_detection = {}
                for col, info in quality['outlier_detection'].items():
                    if isinstance(info, dict) and 'indices' in info:
                        outlier_detection[col] = {
                            'count': info.get('count', 0),
                            'percentage': info.get('percentage', 0.0),
                            'bounds': info.get('bounds', {}),
                        }
                    else:
                        outlier_detection[col] = info
                quality['outlier_detection'] = outlier_detection
            
            if 'duplicate_check' in quality and isinstance(quality['duplicate_check'], dict):
                duplicate = quality['duplicate_check'].copy()
                if 'indices' in duplicate:
                    duplicate['indices'] = duplicate['indices'][:10] if isinstance(duplicate['indices'], list) else []
                quality['duplicate_check'] = duplicate
            
            summary['quality_analysis'] = quality
        
        # 保留相关性分析摘要（移除完整矩阵）
        if 'correlations' in analysis_result:
            correlations = analysis_result['correlations'].copy()
            correlations.pop('pearson_matrix', None)
            correlations.pop('spearman_matrix', None)
            
            if 'correlations' in correlations and isinstance(correlations['correlations'], list):
                correlations['correlations'] = correlations['correlations'][:10]
            
            summary['correlations'] = correlations
        
        # 保留统计检验摘要
        if 'statistical_tests' in analysis_result:
            stats = analysis_result['statistical_tests'].copy()
            
            if 'normality_tests' in stats and isinstance(stats['normality_tests'], dict):
                normality_tests = dict(list(stats['normality_tests'].items())[:20])
                stats['normality_tests'] = normality_tests
            
            summary['statistical_tests'] = stats
        
        return summary
    
    @staticmethod
    def save_analysis_record(uid: str, filename: str, storage_url: str, analysis_result: Dict) -> Optional[str]:
        """保存分析记录到 Firestore"""
        try:
            db = HistoryService._get_firestore_client()
            
            summary = HistoryService._prepare_analysis_summary(analysis_result)
            
            quality_score = None
            if 'quality_analysis' in analysis_result:
                quality_analysis = analysis_result['quality_analysis']
                if isinstance(quality_analysis, dict):
                    quality_score = quality_analysis.get('quality_score')
            
            record = {
                'filename': filename,
                'storage_url': storage_url,
                'quality_score': quality_score,
                'summary': summary,
                'created_at': SERVER_TIMESTAMP,
            }
            
            doc_ref = db.collection('users').document(uid).collection('history').document()
            doc_ref.set(record)
            
            logger.info(f"Saved analysis record for user {uid}: {doc_ref.id}")
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Failed to save analysis record: {e}")
            return None
    
    @staticmethod
    def get_user_history(uid: str, limit: int = 20) -> List[Dict]:
        """获取用户的分析历史"""
        try:
            db = HistoryService._get_firestore_client()
            
            docs = (
                db.collection('users')
                .document(uid)
                .collection('history')
                .order_by('created_at', direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream()
            )
            
            history = []
            for doc in docs:
                record = doc.to_dict()
                record['id'] = doc.id
                history.append(record)
            
            logger.info(f"Retrieved {len(history)} history records for user {uid}")
            return history
            
        except Exception as e:
            logger.error(f"Failed to get user history: {e}")
            return []
