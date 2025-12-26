"""
SentinEL 推荐系统训练数据生成器

生成冷启动数据用于训练双塔推荐模型：
1. strategies.csv - 挽留策略库 (120+ 策略)
2. user_interactions.csv - 用户-策略交互记录 (10,000 条)

交互逻辑:
- 高风险用户 (risk_score > 0.7) 倾向于高折扣策略
- 中风险用户 (0.4 <= risk_score <= 0.7) 偏好功能解锁
- 低风险用户 (risk_score < 0.4) 可被简单邮件挽留

使用方法:
    python -m ml_engine.data.generate_recsys_data
    
输出:
    ml_engine/data/strategies.csv
    ml_engine/data/user_interactions.csv
"""

import os
import random
import csv
import logging
from typing import List, Dict, Tuple
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 设置随机种子保证可复现
random.seed(42)

# ==============================================================================
# 策略模板定义
# ==============================================================================

DISCOUNT_TEMPLATES = [
    ("首月{discount}%折扣优惠", 5, 50),
    ("年度订阅{discount}%优惠", 10, 40),
    ("续费立减{discount}%", 5, 35),
    ("VIP专属{discount}%折扣", 15, 45),
    ("限时促销{discount}%OFF", 10, 50),
    ("老用户回归{discount}%优惠", 20, 50),
    ("季度套餐{discount}%折扣", 8, 30),
    ("升级套餐享{discount}%优惠", 12, 40),
]

FEATURE_UNLOCK_TEMPLATES = [
    ("免费试用高级功能{days}天", 7, 30),
    ("解锁专属AI分析{days}天", 14, 45),
    ("赠送云存储空间{gb}GB", 10, 100),
    ("开放API调用额度{calls}次/月", 100, 10000),
    ("专属客服支持{days}天", 7, 30),
    ("数据导出功能{days}天试用", 7, 14),
    ("团队协作功能{days}天体验", 14, 30),
    ("自定义报表{days}天免费", 7, 21),
]

EMAIL_TEMPLATES = [
    ("个性化产品使用技巧邮件", 0, 5),
    ("专属客户经理联系邮件", 2, 8),
    ("产品更新亮点通知", 0, 3),
    ("用户成功案例分享", 0, 5),
    ("满意度调查邀请", 0, 3),
    ("节日问候与专属福利", 1, 10),
    ("产品路线图预览邮件", 0, 5),
    ("一对一产品咨询邀请", 5, 15),
]

REGIONS = ["north", "south", "east", "west", "central", "overseas"]


def generate_strategies() -> List[Dict]:
    """
    生成策略库
    
    Returns:
        List[Dict]: 策略列表，每个策略包含 strategy_id, type, cost, description
    """
    strategies = []
    strategy_id = 1
    
    # 生成折扣策略 (40个)
    for template, cost_min, cost_max in DISCOUNT_TEMPLATES:
        for _ in range(5):
            discount = random.randint(10, 50)
            cost = random.randint(cost_min, cost_max)
            description = template.format(discount=discount)
            strategies.append({
                "strategy_id": f"S{strategy_id:04d}",
                "type": "discount",
                "cost": cost,
                "description": description
            })
            strategy_id += 1
    
    # 生成功能解锁策略 (40个)
    for template, val_min, val_max in FEATURE_UNLOCK_TEMPLATES:
        for _ in range(5):
            if "days" in template:
                val = random.randint(val_min, val_max)
                description = template.format(days=val)
            elif "gb" in template.lower():
                val = random.randint(val_min, val_max)
                description = template.format(gb=val)
            else:
                val = random.randint(val_min, val_max)
                description = template.format(calls=val)
            cost = random.randint(5, 25)  # 功能解锁成本较低
            strategies.append({
                "strategy_id": f"S{strategy_id:04d}",
                "type": "feature_unlock",
                "cost": cost,
                "description": description
            })
            strategy_id += 1
    
    # 生成邮件策略 (40个)
    for template, cost_min, cost_max in EMAIL_TEMPLATES:
        for _ in range(5):
            cost = random.randint(cost_min, cost_max)
            strategies.append({
                "strategy_id": f"S{strategy_id:04d}",
                "type": "email",
                "cost": cost,
                "description": template
            })
            strategy_id += 1
    
    logger.info(f"生成 {len(strategies)} 个策略")
    return strategies


def select_strategy_by_risk(
    risk_score: float, 
    strategies: List[Dict]
) -> Tuple[Dict, int]:
    """
    根据用户风险等级选择策略并模拟结果
    
    高风险用户 (>0.7): 偏好高成本折扣，成功率与成本正相关
    中风险用户 (0.4-0.7): 偏好功能解锁
    低风险用户 (<0.4): 简单邮件即可
    
    Args:
        risk_score: 用户风险分数 (0.0 - 1.0)
        strategies: 策略库
        
    Returns:
        Tuple[Dict, int]: (选中的策略, 挽留结果 1=成功/0=失败)
    """
    # 按类型分组
    discounts = [s for s in strategies if s["type"] == "discount"]
    features = [s for s in strategies if s["type"] == "feature_unlock"]
    emails = [s for s in strategies if s["type"] == "email"]
    
    if risk_score > 0.7:
        # 高风险: 80% 选折扣, 15% 功能, 5% 邮件
        pool_choice = random.random()
        if pool_choice < 0.8:
            # 偏好高成本策略
            high_cost = [s for s in discounts if s["cost"] >= 30]
            strategy = random.choice(high_cost if high_cost else discounts)
            # 高成本策略更可能成功
            success_prob = 0.3 + (strategy["cost"] / 100) * 0.5
        elif pool_choice < 0.95:
            strategy = random.choice(features)
            success_prob = 0.25
        else:
            strategy = random.choice(emails)
            success_prob = 0.1
    
    elif risk_score > 0.4:
        # 中风险: 40% 功能, 35% 折扣, 25% 邮件
        pool_choice = random.random()
        if pool_choice < 0.4:
            strategy = random.choice(features)
            success_prob = 0.5
        elif pool_choice < 0.75:
            strategy = random.choice(discounts)
            success_prob = 0.4
        else:
            strategy = random.choice(emails)
            success_prob = 0.35
    
    else:
        # 低风险: 60% 邮件, 25% 功能, 15% 折扣
        pool_choice = random.random()
        if pool_choice < 0.6:
            strategy = random.choice(emails)
            success_prob = 0.7  # 低风险用户对邮件响应好
        elif pool_choice < 0.85:
            strategy = random.choice(features)
            success_prob = 0.65
        else:
            strategy = random.choice(discounts)
            success_prob = 0.6
    
    # 根据成功概率模拟结果
    outcome = 1 if random.random() < success_prob else 0
    
    return strategy, outcome


def generate_interactions(
    strategies: List[Dict], 
    num_interactions: int = 10000
) -> List[Dict]:
    """
    生成用户-策略交互记录
    
    Args:
        strategies: 策略库
        num_interactions: 交互数量
        
    Returns:
        List[Dict]: 交互记录列表
    """
    interactions = []
    
    for i in range(num_interactions):
        # 生成用户 ID
        user_id = f"U{random.randint(1, 5000):05d}"
        
        # 生成风险分数 (略微偏向中高风险，因为这些用户更需要挽留)
        risk_distribution = random.random()
        if risk_distribution < 0.3:
            risk_score = round(random.uniform(0.0, 0.4), 2)  # 低风险
        elif risk_distribution < 0.6:
            risk_score = round(random.uniform(0.4, 0.7), 2)  # 中风险
        else:
            risk_score = round(random.uniform(0.7, 1.0), 2)  # 高风险
        
        # 随机区域
        region = random.choice(REGIONS)
        
        # 选择策略并模拟结果
        strategy, outcome = select_strategy_by_risk(risk_score, strategies)
        
        interactions.append({
            "user_id": user_id,
            "user_risk_score": risk_score,
            "user_region": region,
            "strategy_id": strategy["strategy_id"],
            "outcome": outcome
        })
    
    # 统计
    success_count = sum(1 for i in interactions if i["outcome"] == 1)
    logger.info(f"生成 {num_interactions} 条交互记录")
    logger.info(f"总体挽留成功率: {success_count / num_interactions * 100:.1f}%")
    
    return interactions


def save_to_csv(data: List[Dict], filepath: str):
    """
    保存数据到 CSV 文件
    
    Args:
        data: 数据列表
        filepath: 输出文件路径
    """
    if not data:
        logger.warning(f"数据为空，跳过保存: {filepath}")
        return
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # 写入 CSV
    fieldnames = list(data[0].keys())
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    logger.info(f"已保存到: {filepath}")


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("SentinEL 推荐系统数据生成器")
    logger.info("=" * 60)
    
    # 获取输出目录
    script_dir = Path(__file__).parent
    
    # 1. 生成策略库
    logger.info("\n[Phase 1] 生成策略库...")
    strategies = generate_strategies()
    strategies_path = script_dir / "strategies.csv"
    save_to_csv(strategies, str(strategies_path))
    
    # 2. 生成交互记录
    logger.info("\n[Phase 2] 生成交互记录...")
    interactions = generate_interactions(strategies, num_interactions=10000)
    interactions_path = script_dir / "user_interactions.csv"
    save_to_csv(interactions, str(interactions_path))
    
    # 3. 打印统计信息
    logger.info("\n" + "=" * 60)
    logger.info("数据生成完成!")
    logger.info("=" * 60)
    
    # 按策略类型统计成功率
    from collections import defaultdict
    type_stats = defaultdict(lambda: {"total": 0, "success": 0})
    
    strategy_map = {s["strategy_id"]: s for s in strategies}
    for inter in interactions:
        s_type = strategy_map[inter["strategy_id"]]["type"]
        type_stats[s_type]["total"] += 1
        type_stats[s_type]["success"] += inter["outcome"]
    
    logger.info("\n按策略类型统计:")
    for s_type, stats in type_stats.items():
        rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        logger.info(f"  {s_type}: {stats['total']} 次, 成功率 {rate:.1f}%")
    
    # 按风险等级统计
    risk_stats = defaultdict(lambda: {"total": 0, "success": 0})
    for inter in interactions:
        if inter["user_risk_score"] > 0.7:
            level = "高风险"
        elif inter["user_risk_score"] > 0.4:
            level = "中风险"
        else:
            level = "低风险"
        risk_stats[level]["total"] += 1
        risk_stats[level]["success"] += inter["outcome"]
    
    logger.info("\n按风险等级统计:")
    for level in ["低风险", "中风险", "高风险"]:
        stats = risk_stats[level]
        rate = stats["success"] / stats["total"] * 100 if stats["total"] > 0 else 0
        logger.info(f"  {level}: {stats['total']} 次, 成功率 {rate:.1f}%")


if __name__ == "__main__":
    main()
