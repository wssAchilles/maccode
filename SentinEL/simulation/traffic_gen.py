#!/usr/bin/env python3
"""
SentinEL Traffic Simulator (负载生成器)

用途: 模拟真实用户流量，对 Cloud Run 后端进行压力测试
作者: SRE Team

运行方式:
  - 本地: python traffic_gen.py
  - Cloud Run Job: 通过 deploy_simulation.sh 部署后执行
"""

import random
import time
import requests
from datetime import datetime


# ============================================
# 配置
# ============================================
API_ENDPOINT = "https://sentinel-backend-kijag7ukkq-uc.a.run.app/api/v1/analyze"
USER_ID_MIN = 1
USER_ID_MAX = 100000
SLEEP_MIN = 2.0  # 最小间隔 (秒)
SLEEP_MAX = 5.0  # 最大间隔 (秒)


def generate_traffic():
    """
    无限循环发送请求，模拟真实用户访问模式
    """
    request_count = 0
    success_count = 0
    error_count = 0
    
    print("=" * 50)
    print("🚀 SentinEL Traffic Simulator 启动")
    print(f"📍 目标: {API_ENDPOINT}")
    print(f"👤 用户ID范围: {USER_ID_MIN} - {USER_ID_MAX}")
    print(f"⏱️  请求间隔: {SLEEP_MIN}s - {SLEEP_MAX}s")
    print("=" * 50)
    
    while True:
        # 生成随机用户 ID
        user_id = random.randint(USER_ID_MIN, USER_ID_MAX)
        request_count += 1
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # 发送 POST 请求
            response = requests.post(
                API_ENDPOINT,
                json={"user_id": str(user_id)},
                headers={"Content-Type": "application/json"},
                timeout=30  # 30秒超时
            )
            
            if response.ok:
                data = response.json()
                risk_level = data.get("risk_level", "Unknown")
                churn_prob = data.get("churn_probability", 0)
                success_count += 1
                
                # 日志输出 (Cloud Run 自动采集)
                print(
                    f"[{timestamp}] ✅ #{request_count} | "
                    f"User: {user_id} | "
                    f"Risk: {risk_level} | "
                    f"Churn: {churn_prob:.2%} | "
                    f"Status: {response.status_code} | "
                    f"Latency: {response.elapsed.total_seconds():.2f}s"
                )
            else:
                error_count += 1
                print(
                    f"[{timestamp}] ❌ #{request_count} | "
                    f"User: {user_id} | "
                    f"Status: {response.status_code} | "
                    f"Error: {response.text[:100]}"
                )
                
        except requests.exceptions.Timeout:
            error_count += 1
            print(f"[{timestamp}] ⏰ #{request_count} | User: {user_id} | TIMEOUT")
            
        except requests.exceptions.RequestException as e:
            error_count += 1
            print(f"[{timestamp}] 💥 #{request_count} | User: {user_id} | Error: {e}")
        
        # 打印统计信息 (每 10 次请求)
        if request_count % 10 == 0:
            success_rate = (success_count / request_count) * 100 if request_count > 0 else 0
            print(
                f"\n📊 统计 | 总请求: {request_count} | "
                f"成功: {success_count} | 失败: {error_count} | "
                f"成功率: {success_rate:.1f}%\n"
            )
        
        # 随机等待，模拟真实用户行为
        sleep_time = random.uniform(SLEEP_MIN, SLEEP_MAX)
        time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        generate_traffic()
    except KeyboardInterrupt:
        print("\n\n🛑 Traffic Simulator 已停止")
