"""
集成示例 - 负载预测 + 优化调度
Integrated Example - Load Prediction + Optimization Scheduling

展示如何将机器学习预测和优化调度结合使用
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from back.services.ml_service import EnergyPredictor
from back.services.optimization_service import EnergyOptimizer


def integrated_workflow():
    """
    完整工作流程: 预测 → 优化 → 调度
    """
    print("\n" + "🌟 " + "="*76)
    print("智能能源管理系统 - 集成工作流程")
    print("="*78 + "\n")
    
    # ========================================================================
    # 步骤 1: 负载预测
    # ========================================================================
    print("【步骤 1】负载预测")
    print("="*80)
    
    # 初始化预测器
    predictor = EnergyPredictor()
    predictor.load_model()
    
    # 预测明天的负载
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    # 模拟温度预测（可以从天气API获取）
    temp_forecast = [
        24.0, 23.5, 23.0, 22.8, 22.5, 23.0,  # 00:00-05:00 (夜间)
        24.0, 25.0, 26.5, 28.0, 29.5, 30.5,  # 06:00-11:00 (升温)
        31.0, 31.5, 31.8, 31.5, 31.0, 30.0,  # 12:00-17:00 (高温)
        28.5, 27.0, 26.0, 25.5, 25.0, 24.5   # 18:00-23:00 (降温)
    ]
    
    print(f"📅 预测日期: {tomorrow.strftime('%Y-%m-%d')}")
    print(f"🌡️  温度范围: {min(temp_forecast):.1f}°C - {max(temp_forecast):.1f}°C")
    
    # 执行预测
    predictions = predictor.predict_next_24h(
        start_time=tomorrow,
        temp_forecast_list=temp_forecast
    )
    
    # 提取负载和电价
    load_profile = [p['predicted_load'] for p in predictions]
    price_profile = [p['price'] for p in predictions]
    
    print(f"\n✓ 预测完成:")
    print(f"   - 平均负载: {np.mean(load_profile):.2f} kW")
    print(f"   - 峰值负载: {np.max(load_profile):.2f} kW")
    print(f"   - 谷值负载: {np.min(load_profile):.2f} kW")
    
    # ========================================================================
    # 步骤 2: 优化调度
    # ========================================================================
    print("\n【步骤 2】优化电池调度")
    print("="*80)
    
    # 初始化优化器
    optimizer = EnergyOptimizer(
        battery_capacity=13.5,  # Tesla Powerwall
        max_power=5.0,
        efficiency=0.95
    )
    
    # 执行优化
    result = optimizer.optimize_schedule(
        load_profile=load_profile,
        price_profile=price_profile,
        initial_soc=0.5  # 假设当前电量 50%
    )
    
    # ========================================================================
    # 步骤 3: 结果分析
    # ========================================================================
    print("\n【步骤 3】结果分析")
    print("="*80)
    
    if result['status'] == 'Optimal':
        # 显示优化调度
        optimizer.print_schedule(result)
        
        # 详细分析
        print("【步骤 4】详细分析")
        print("="*80)
        
        schedule = result['schedule']
        df = pd.DataFrame(schedule)
        
        # 按电价时段分组
        print("\n📊 按电价时段统计:")
        price_groups = df.groupby('price').agg({
            'load': 'mean',
            'battery_action': 'sum',
            'hour': 'count'
        }).round(2)
        
        for price, row in price_groups.iterrows():
            period = "谷时" if price == 0.3 else ("平时" if price == 0.6 else "峰时")
            print(f"   {period} ({price}元): 平均负载 {row['load']:.0f} kW, "
                  f"电池动作 {row['battery_action']:.2f} kWh, "
                  f"{int(row['hour'])} 小时")
        
        # 充放电分析
        charging = df[df['battery_action'] > 0.01]
        discharging = df[df['battery_action'] < -0.01]
        
        print(f"\n⚡ 充电策略:")
        if len(charging) > 0:
            print(f"   - 充电时段: {len(charging)} 小时")
            print(f"   - 总充电量: {charging['charge_power'].sum():.2f} kWh")
            print(f"   - 平均电价: {charging['price'].mean():.2f} 元/kWh")
            print(f"   - 充电时刻: {', '.join([f'{int(h):02d}:00' for h in charging['hour']])}")
        else:
            print(f"   - 无充电")
        
        print(f"\n🔋 放电策略:")
        if len(discharging) > 0:
            print(f"   - 放电时段: {len(discharging)} 小时")
            print(f"   - 总放电量: {discharging['discharge_power'].sum():.2f} kWh")
            print(f"   - 平均电价: {discharging['price'].mean():.2f} 元/kWh")
            print(f"   - 放电时刻: {', '.join([f'{int(h):02d}:00' for h in discharging['hour']])}")
        else:
            print(f"   - 无放电")
        
        # 成本效益分析
        print(f"\n💰 成本效益分析:")
        print(f"   - 预测总负载: {df['load'].sum():.2f} kWh")
        print(f"   - 无电池成本: {result['total_cost_without_battery']:.2f} 元")
        print(f"   - 有电池成本: {result['total_cost_with_battery']:.2f} 元")
        print(f"   - 节省金额: {result['savings']:.2f} 元")
        print(f"   - 节省比例: {result['savings_percent']:.1f}%")
        
        # ROI 分析（假设电池成本）
        battery_cost = 50000  # 假设电池系统成本 5万元
        daily_savings = result['savings']
        annual_savings = daily_savings * 365
        payback_years = battery_cost / annual_savings if annual_savings > 0 else float('inf')
        
        print(f"\n📈 投资回报分析 (假设电池成本 {battery_cost:,} 元):")
        print(f"   - 日节省: {daily_savings:.2f} 元")
        print(f"   - 年节省: {annual_savings:.2f} 元")
        print(f"   - 回本周期: {payback_years:.1f} 年")
        
        # 可视化建议
        print(f"\n📊 可视化建议:")
        print(f"   1. 绘制负载预测曲线")
        print(f"   2. 绘制电池 SOC 变化曲线")
        print(f"   3. 绘制充放电功率曲线")
        print(f"   4. 对比有无电池的成本差异")
        
        # 导出结果
        print(f"\n💾 导出结果:")
        output_file = Path(__file__).parent.parent.parent / 'data' / 'output' / 'optimization_result.csv'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_file, index=False)
        print(f"   ✓ 结果已保存到: {output_file}")
        
    else:
        print(f"\n❌ 优化失败: {result.get('error', 'Unknown error')}")
    
    # ========================================================================
    # 总结
    # ========================================================================
    print("\n" + "="*80)
    print("✅ 集成工作流程完成!")
    print("="*80)
    
    if result['status'] == 'Optimal':
        print(f"\n🎯 关键结论:")
        print(f"   1. 机器学习模型成功预测未来24小时负载")
        print(f"   2. 优化算法制定了最优充放电策略")
        print(f"   3. 电池储能系统可节省 {result['savings']:.2f} 元 ({result['savings_percent']:.1f}%)")
        print(f"   4. 策略: 谷时充电，峰时放电")
        print(f"\n💡 下一步:")
        print(f"   - 将此工作流程集成到 API 服务")
        print(f"   - 创建前端界面展示预测和优化结果")
        print(f"   - 实现实时监控和自动调度")
        print(f"   - 接入实际的电池管理系统 (BMS)")
    
    print()


def compare_scenarios():
    """
    场景对比: 不同电池配置的效果
    """
    print("\n" + "🔬 " + "="*76)
    print("场景对比分析")
    print("="*78 + "\n")
    
    # 准备预测数据
    predictor = EnergyPredictor()
    predictor.load_model()
    
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    predictions = predictor.predict_next_24h(start_time=tomorrow)
    
    load_profile = [p['predicted_load'] for p in predictions]
    price_profile = [p['price'] for p in predictions]
    
    # 测试不同电池配置
    scenarios = [
        {"name": "无电池", "capacity": 0, "power": 0},
        {"name": "小型电池 (10kWh)", "capacity": 10, "power": 3},
        {"name": "Tesla Powerwall (13.5kWh)", "capacity": 13.5, "power": 5},
        {"name": "大型电池 (20kWh)", "capacity": 20, "power": 7},
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n📦 场景: {scenario['name']}")
        print("-" * 80)
        
        if scenario['capacity'] == 0:
            # 无电池场景
            cost = sum(l * p for l, p in zip(load_profile, price_profile))
            results.append({
                'scenario': scenario['name'],
                'cost': cost,
                'savings': 0,
                'savings_percent': 0
            })
            print(f"   总成本: {cost:.2f} 元")
        else:
            # 有电池场景
            optimizer = EnergyOptimizer(
                battery_capacity=scenario['capacity'],
                max_power=scenario['power'],
                efficiency=0.95
            )
            
            result = optimizer.optimize_schedule(
                load_profile=load_profile,
                price_profile=price_profile,
                initial_soc=0.5
            )
            
            if result['status'] == 'Optimal':
                results.append({
                    'scenario': scenario['name'],
                    'cost': result['total_cost_with_battery'],
                    'savings': result['savings'],
                    'savings_percent': result['savings_percent']
                })
                print(f"   总成本: {result['total_cost_with_battery']:.2f} 元")
                print(f"   节省: {result['savings']:.2f} 元 ({result['savings_percent']:.1f}%)")
    
    # 对比总结
    print("\n" + "="*80)
    print("📊 场景对比总结")
    print("="*80 + "\n")
    
    df_results = pd.DataFrame(results)
    print(df_results.to_string(index=False))
    
    print(f"\n💡 结论:")
    best = df_results.loc[df_results['savings'].idxmax()]
    print(f"   - 最佳配置: {best['scenario']}")
    print(f"   - 最大节省: {best['savings']:.2f} 元 ({best['savings_percent']:.1f}%)")
    print()


if __name__ == "__main__":
    # 运行集成工作流程
    integrated_workflow()
    
    # 运行场景对比（可选）
    # compare_scenarios()
