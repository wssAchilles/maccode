"""
SentinEL 存储服务
负责将分析结果持久化到 Google Cloud Firestore
"""

from google.cloud import firestore
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from datetime import datetime
import re
from typing import Optional


class StorageService:
    """
    Firestore 存储服务
    用于记录分析日志，支持后续审计和分析
    """
    
    def __init__(self):
        # 初始化 Firestore 客户端
        # 使用默认凭证 (Application Default Credentials)
        self.db = firestore.Client()
        self.collection_name = "analysis_logs"
    
    def save_analysis_result(
        self,
        user_id: str,
        churn_probability: float,
        risk_level: str,
        generated_email: Optional[str],
        processing_time_ms: float,
        analysis_id: Optional[str] = None
    ) -> str:
        """
        保存分析结果到 Firestore
        
        Args:
            user_id: 用户 ID
            churn_probability: 流失概率 (0-1)
            risk_level: 风险等级 ("High" / "Low")
            generated_email: AI 生成的邮件内容 (可为 None)
            processing_time_ms: 处理耗时 (毫秒)
            analysis_id: 可选的预生成文档 ID
        
        Returns:
            str: 文档 ID
        """
        # 从生成的邮件中提取主题 (如果存在)
        email_subject = self._extract_email_subject(generated_email)
        
        # 构建文档数据
        doc_data = {
            "user_id": user_id,
            "churn_probability": churn_probability,
            "risk_level": risk_level,
            "email_subject": email_subject,
            "processing_time_ms": processing_time_ms,
            "timestamp": SERVER_TIMESTAMP,  # 使用 Firestore 服务器时间
            "created_at_local": datetime.utcnow().isoformat(),  # 备用本地时间
        }
        
        # 写入 Firestore
        if analysis_id:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
        else:
            doc_ref = self.db.collection(self.collection_name).document()
            
        doc_ref.set(doc_data)
        
        print(f"[StorageService] 已保存分析日志: {doc_ref.id} for user {user_id}")
        return doc_ref.id

    def generate_id(self) -> str:
        """生成一个新的唯一文档 ID"""
        return self.db.collection(self.collection_name).document().id
    
    def _extract_email_subject(self, email_content: Optional[str]) -> Optional[str]:
        """
        从邮件内容中提取主题行
        
        Args:
            email_content: 邮件全文
        
        Returns:
            str | None: 邮件主题
        """
        if not email_content:
            return None
        
        # 尝试多种模式匹配邮件主题
        patterns = [
            r"Subject:\s*(.+?)(?:\n|$)",    # 英文格式
            r"主题[:：]\s*(.+?)(?:\n|$)",    # 中文格式
            r"\*\*主题\*\*[:：]?\s*(.+?)(?:\n|$)",  # Markdown 格式
        ]
        
        for pattern in patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # 如果没找到显式主题，返回邮件前 50 个字符作为摘要
        return email_content[:50].replace("\n", " ").strip() + "..."
    
    def get_recent_logs(self, limit: int = 10) -> list:
        """
        获取最近的分析日志 (用于 Dashboard 展示)
        
        Args:
            limit: 返回记录数量
        
        Returns:
            list: 最近的分析记录列表
        """
        logs = []
        docs = (
            self.db.collection(self.collection_name)
            .order_by("timestamp", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        
        for doc in docs:
            data = doc.to_dict()
            data["doc_id"] = doc.id
            logs.append(data)
        
        return logs


    def update_feedback(self, analysis_id: str, feedback_type: str) -> bool:
        """
        更新分析记录的用户反馈
        
        Args:
            analysis_id: 分析记录 ID (Firestore Document ID)
            feedback_type: 反馈类型 ("thumbs_up" / "thumbs_down")
        
        Returns:
            bool: 是否更新成功
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc_ref.update({
                "feedback": feedback_type,
                "feedback_timestamp": SERVER_TIMESTAMP
            })
            print(f"[StorageService] Feedback updated for analysis {analysis_id}: {feedback_type}")
            return True
        except Exception as e:
            print(f"[StorageService] Error updating feedback: {e}")
            return False

    def update_audit_result(self, analysis_id: str, audit_data: dict) -> bool:
        """
        Updates the analysis record with AI Judge audit results.
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            doc_ref.update({
                "audit_score": audit_data.get("score"),
                "audit_reason": audit_data.get("reasoning"),
                "audit_flags": audit_data.get("flags", []),
                "audit_timestamp": firestore.SERVER_TIMESTAMP
            })
            print(f"[StorageService] Audit result updated for {analysis_id}")
            return True
        except Exception as e:
            print(f"[StorageService] Error updating audit result for {analysis_id}: {e}")
            return False

    def create_queued_analysis(self, user_id: str, analysis_id: str) -> None:
        """
        创建初始状态为 QUEUED 的分析记录 (异步模式)
        
        Args:
            user_id: 用户 ID
            analysis_id: 预生成的分析 ID
        """
        doc_ref = self.db.collection(self.collection_name).document(analysis_id)
        doc_ref.set({
            "user_id": user_id,
            "status": "QUEUED",
            "timestamp": SERVER_TIMESTAMP,
            "created_at_local": datetime.utcnow().isoformat(),
        })
        print(f"[StorageService] Created QUEUED analysis: {analysis_id} for user {user_id}")

    def update_status(
        self,
        analysis_id: str,
        status: str,
        **kwargs
    ) -> bool:
        """
        更新分析记录状态
        
        Args:
            analysis_id: 分析记录 ID
            status: 新状态 (QUEUED / PROCESSING / COMPLETED / FAILED)
            **kwargs: 额外要更新的字段 (如 result, error_message 等)
        
        Returns:
            bool: 是否更新成功
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(analysis_id)
            update_data = {
                "status": status,
                "updated_at": SERVER_TIMESTAMP,
                **kwargs
            }
            doc_ref.update(update_data)
            print(f"[StorageService] Status updated for {analysis_id}: {status}")
            return True
        except Exception as e:
            print(f"[StorageService] Error updating status for {analysis_id}: {e}")
            return False


# 创建单例实例
_storage_service_instance = None

def get_storage_service() -> Optional["StorageService"]:
    global _storage_service_instance
    if _storage_service_instance is None:
        try:
            _storage_service_instance = StorageService()
        except Exception as e:
            print(f"Failed to initialize StorageService: {e}")
            return None
    return _storage_service_instance
