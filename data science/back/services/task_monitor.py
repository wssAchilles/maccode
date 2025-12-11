"""
任务监控服务 - 记录和监控定时任务执行状态
Task Monitor Service for Cron Job Execution Tracking

功能:
1. 记录每次任务执行的状态、耗时、错误信息
2. 提供任务执行历史查询
3. 支持告警通知（可扩展）
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TaskMonitor:
    """
    任务监控器
    
    记录定时任务的执行状态到 Firestore，便于监控和排查问题
    """
    
    def __init__(self):
        """初始化监控器"""
        self._firestore_client = None
        self._collection_name = 'task_executions'
    
    @property
    def firestore(self):
        """延迟初始化 Firestore 客户端"""
        if self._firestore_client is None:
            try:
                from google.cloud import firestore
                self._firestore_client = firestore.Client()
            except Exception as e:
                logger.warning(f"Firestore 初始化失败: {e}")
                return None
        return self._firestore_client
    
    def record_task_start(self, task_name: str, metadata: Dict = None) -> Optional[str]:
        """
        记录任务开始
        
        Args:
            task_name: 任务名称 ('fetch_data' 或 'train_model')
            metadata: 额外的元数据
            
        Returns:
            执行记录 ID，失败返回 None
        """
        if self.firestore is None:
            logger.warning("Firestore 不可用，跳过任务记录")
            return None
        
        try:
            doc_ref = self.firestore.collection(self._collection_name).document()
            
            record = {
                'task_name': task_name,
                'status': TaskStatus.STARTED.value,
                'started_at': datetime.now(timezone.utc),
                'ended_at': None,
                'duration_seconds': None,
                'error_message': None,
                'metadata': metadata or {},
                'environment': 'gae' if os.getenv('GAE_ENV') else 'local'
            }
            
            doc_ref.set(record)
            logger.info(f"📝 任务开始记录: {task_name} (ID: {doc_ref.id})")
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"记录任务开始失败: {e}")
            return None
    
    def record_task_end(
        self, 
        execution_id: str, 
        status: TaskStatus, 
        error_message: str = None,
        result_metadata: Dict = None
    ):
        """
        记录任务结束
        
        Args:
            execution_id: 执行记录 ID
            status: 任务状态
            error_message: 错误信息（如果失败）
            result_metadata: 结果元数据
        """
        if self.firestore is None or execution_id is None:
            return
        
        try:
            doc_ref = self.firestore.collection(self._collection_name).document(execution_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                logger.warning(f"执行记录不存在: {execution_id}")
                return
            
            data = doc.to_dict()
            started_at = data.get('started_at')
            ended_at = datetime.now(timezone.utc)
            
            # 计算耗时
            duration = None
            if started_at:
                if hasattr(started_at, 'timestamp'):
                    duration = (ended_at - started_at).total_seconds()
            
            update_data = {
                'status': status.value,
                'ended_at': ended_at,
                'duration_seconds': duration,
                'error_message': error_message
            }
            
            if result_metadata:
                update_data['result_metadata'] = result_metadata
            
            doc_ref.update(update_data)
            
            status_emoji = "✅" if status == TaskStatus.SUCCESS else "❌"
            logger.info(f"{status_emoji} 任务结束记录: {data.get('task_name')} "
                       f"(耗时: {duration:.1f}s)" if duration else "")
            
        except Exception as e:
            logger.error(f"记录任务结束失败: {e}")
    
    def get_recent_executions(self, task_name: str = None, limit: int = 10) -> list:
        """
        获取最近的任务执行记录
        
        Args:
            task_name: 任务名称（可选，不指定则返回所有）
            limit: 返回数量限制
            
        Returns:
            执行记录列表
        """
        if self.firestore is None:
            return []
        
        try:
            query = self.firestore.collection(self._collection_name)
            
            if task_name:
                query = query.where('task_name', '==', task_name)
            
            query = query.order_by('started_at', direction='DESCENDING').limit(limit)
            
            results = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                # 转换时间戳为 ISO 格式
                if data.get('started_at'):
                    data['started_at'] = data['started_at'].isoformat()
                if data.get('ended_at'):
                    data['ended_at'] = data['ended_at'].isoformat()
                results.append(data)
            
            return results
            
        except Exception as e:
            logger.error(f"获取执行记录失败: {e}")
            return []
    
    def get_task_stats(self, task_name: str, days: int = 7) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Args:
            task_name: 任务名称
            days: 统计天数
            
        Returns:
            统计信息字典
        """
        if self.firestore is None:
            return {}
        
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = (self.firestore.collection(self._collection_name)
                    .where('task_name', '==', task_name)
                    .where('started_at', '>=', cutoff_time))
            
            total = 0
            success = 0
            failed = 0
            total_duration = 0
            
            for doc in query.stream():
                data = doc.to_dict()
                total += 1
                
                if data.get('status') == TaskStatus.SUCCESS.value:
                    success += 1
                elif data.get('status') == TaskStatus.FAILED.value:
                    failed += 1
                
                if data.get('duration_seconds'):
                    total_duration += data['duration_seconds']
            
            return {
                'task_name': task_name,
                'period_days': days,
                'total_executions': total,
                'success_count': success,
                'failed_count': failed,
                'success_rate': (success / total * 100) if total > 0 else 0,
                'avg_duration_seconds': (total_duration / total) if total > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"获取任务统计失败: {e}")
            return {}


# 全局监控器实例
_task_monitor = None


def get_task_monitor() -> TaskMonitor:
    """获取任务监控器单例"""
    global _task_monitor
    if _task_monitor is None:
        _task_monitor = TaskMonitor()
    return _task_monitor
