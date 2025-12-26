"""
SentinEL A/B 测试实验服务
提供多模型动态路由和确定性用户分流
"""

import zlib
import logging
from typing import Tuple, Optional
from firebase_admin import firestore

logger = logging.getLogger(__name__)


class ExperimentService:
    """
    A/B 测试实验服务
    
    功能:
    - 从 Firestore 读取实验配置
    - 使用确定性哈希算法进行用户分流
    - 确保同一用户始终访问同一模型
    """
    
    # 默认配置 (Firestore 不可用时使用)
    DEFAULT_CONFIG = {
        "enabled": True,
        "split_ratio": 0.5,  # 50% 流量给 Group A
        "model_a": "gemini-2.5-pro",     # Group A: 高质量模型
        "model_b": "gemini-2.0-flash"    # Group B: 低延迟模型
    }
    
    def __init__(self):
        self._config_cache: Optional[dict] = None
        self._config_doc_path = "config/ab_testing"
        
        try:
            self.db = firestore.client()
            logger.info("[ExperimentService] Firestore 连接成功")
        except Exception as e:
            logger.warning(f"[ExperimentService] Firestore 连接失败，使用默认配置: {e}")
            self.db = None
    
    def get_config(self) -> dict:
        """
        获取 A/B 测试配置
        
        优先从 Firestore 读取，失败时使用默认配置。
        配置会被缓存以减少 Firestore 读取次数。
        
        Returns:
            dict: 实验配置
        """
        # 使用缓存 (生产环境可加入 TTL 刷新机制)
        if self._config_cache:
            return self._config_cache
        
        if not self.db:
            logger.info("[ExperimentService] 使用默认配置")
            return self.DEFAULT_CONFIG
        
        try:
            doc_ref = self.db.document(self._config_doc_path)
            doc = doc_ref.get()
            
            if doc.exists:
                self._config_cache = doc.to_dict()
                logger.info(f"[ExperimentService] 配置加载成功: {self._config_cache}")
                return self._config_cache
            else:
                logger.warning("[ExperimentService] 配置文档不存在，使用默认配置")
                return self.DEFAULT_CONFIG
                
        except Exception as e:
            logger.error(f"[ExperimentService] 读取配置失败: {e}")
            return self.DEFAULT_CONFIG
    
    def invalidate_cache(self):
        """使配置缓存失效 (用于配置更新后)"""
        self._config_cache = None
        logger.info("[ExperimentService] 配置缓存已清除")
    
    def get_model_for_user(self, user_id: str) -> Tuple[str, str]:
        """
        根据用户 ID 确定实验分组和使用的模型
        
        使用 CRC32 哈希算法确保:
        1. 同一用户始终落入同一分组
        2. 用户分布均匀
        
        Args:
            user_id: 用户 ID
        
        Returns:
            Tuple[str, str]: (experiment_group, model_name)
                - experiment_group: "A" 或 "B"
                - model_name: 具体模型名称
        """
        config = self.get_config()
        
        # 实验未启用时，使用默认模型
        if not config.get("enabled", True):
            logger.info(f"[ExperimentService] 实验已禁用，使用默认模型 A")
            return ("A", config.get("model_a", self.DEFAULT_CONFIG["model_a"]))
        
        # 确定性哈希分流
        # CRC32 产生 32 位无符号整数，取模 100 得到 0-99 的桶号
        hash_value = zlib.crc32(user_id.encode("utf-8")) & 0xffffffff
        bucket = hash_value % 100
        
        split_ratio = config.get("split_ratio", 0.5)
        threshold = int(split_ratio * 100)
        
        if bucket < threshold:
            group = "A"
            model = config.get("model_a", self.DEFAULT_CONFIG["model_a"])
        else:
            group = "B"
            model = config.get("model_b", self.DEFAULT_CONFIG["model_b"])
        
        logger.info(f"[ExperimentService] 用户 {user_id} -> Group {group} ({model}), bucket={bucket}")
        return (group, model)


# 全局单例
experiment_service = ExperimentService()
