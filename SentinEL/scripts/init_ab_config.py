#!/usr/bin/env python3
"""
初始化 A/B 测试配置到 Firestore

用法: python scripts/init_ab_config.py
"""

import firebase_admin
from firebase_admin import credentials, firestore

# 初始化 Firebase (如果尚未初始化)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.client()

# A/B 测试配置
AB_CONFIG = {
    "enabled": True,
    "split_ratio": 0.5,  # 50% 流量给 Group A (Pro), 50% 给 Group B (Flash)
    "model_a": "gemini-2.5-pro",       # Group A: 高质量模型
    "model_b": "gemini-2.0-flash",     # Group B: 低延迟模型
    "description": "SentinEL 邮件生成模型 A/B 测试",
    "created_at": firestore.SERVER_TIMESTAMP
}

def main():
    print("正在写入 A/B 测试配置到 Firestore...")
    
    doc_ref = db.document("config/ab_testing")
    doc_ref.set(AB_CONFIG)
    
    print("✅ 配置写入成功!")
    print(f"   路径: config/ab_testing")
    print(f"   内容: {AB_CONFIG}")

if __name__ == "__main__":
    main()
