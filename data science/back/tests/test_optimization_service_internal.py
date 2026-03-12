"""
优化服务内部测试脚本
提取自 optimization_service.py 的 main 函数
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'back'))

from back.services.optimization_service import EnergyOptimizer

def main():
    """
    主函数 - 测试代码
    """
    print("\n" + "🎯 " + "="*76)
    print("能源优化系统 - 测试脚本")
    print("="*78 + "\n")
    
    try:
        # 1. 创建优化器
        print("【步骤 1】创建 EnergyOptimizer")
        print("-" * 80)
        optimizer = EnergyOptimizer(
            battery_capacity=13.5,  # Tesla Powerwall
            max_power=5.0,
            efficiency=0.95
        )
        
        # 2. 模拟负载和电价数据
        print("\n【步骤 2】准备测试数据")
        print("-" * 80)
        
        # 负载数据: 模拟典型日负载曲线
        load_profile = [
            # 00:00-05:00 (夜间低负载)
            120, 115, 110, 105, 100, 105,
            # 06:00-08:00 (早晨上升)
            130, 160, 200,
            # 09:00-17:00 (白天高负载)
            250, 280, 300, 310, 300, 290, 280, 270, 260,
            # 18:00-22:00 (晚间峰值)
            300, 320, 310, 290,
            # 23:00 (夜间)
            200, 150
        ]
        
        # 峰谷电价
        price_profile = [
            # 00:00-07:00 (谷时)
            0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,
            # 08:00-17:00 (平时)
            0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6,
            # 18:00-21:00 (峰时)
            1.0, 1.0, 1.0, 1.0,
            # 22:00-23:00 (谷时)
            0.3, 0.3
        ]
        
        print(f"✓ 负载数据: 24 小时，范围 {min(load_profile):.0f}-{max(load_profile):.0f} kW")
        print(f"✓ 电价数据: 谷时 0.3元, 平时 0.6元, 峰时 1.0元")
        
        # 3. 运行优化
        print("\n【步骤 3】运行优化")
        print("-" * 80)
        
        result = optimizer.optimize_schedule(
            load_profile=load_profile,
            price_profile=price_profile,
            initial_soc=0.5  # 初始电量 50%
        )
        
        # 4. 显示结果
        print("\n【步骤 4】显示优化结果")
        print("-" * 80)
        
        optimizer.print_schedule(result)
        
        # 5. 分析充放电策略
        if result['status'] == 'Optimal':
            print("【步骤 5】策略分析")
            print("-" * 80)
            
            schedule = result['schedule']
            
            # 统计充放电时段
            charging_hours = [s for s in schedule if s['battery_action'] > 0.01]
            discharging_hours = [s for s in schedule if s['battery_action'] < -0.01]
            
            print(f"\n⚡ 充电时段 ({len(charging_hours)} 小时):")
            for s in charging_hours:
                print(f"   {s['hour']:02d}:00 - 充电 {s['charge_power']:.2f} kW @ {s['price']:.2f}元")
            
            print(f"\n🔋 放电时段 ({len(discharging_hours)} 小时):")
            for s in discharging_hours:
                print(f"   {s['hour']:02d}:00 - 放电 {s['discharge_power']:.2f} kW @ {s['price']:.2f}元")
            
            # 计算总充放电量
            total_charged = sum(s['charge_power'] for s in schedule)
            total_discharged = sum(s['discharge_power'] for s in schedule)
            
            print(f"\n📊 能量统计:")
            print(f"   - 总充电量: {total_charged:.2f} kWh")
            print(f"   - 总放电量: {total_discharged:.2f} kWh")
            if total_charged > 0:
                print(f"   - 循环效率: {(total_discharged / total_charged * 100):.1f}%")
            else:
                print(f"   - 循环效率: N/A (无充电)")
        
        # 总结
        print("\n" + "="*80)
        print("✅ 测试完成!")
        print("="*80)
        
        if result['status'] == 'Optimal':
            print(f"\n💡 优化策略:")
            print(f"   - 在谷时电价时段充电")
            print(f"   - 在峰时电价时段放电")
            print(f"   - 节省电费: {result['savings']:.2f} 元 ({result['savings_percent']:.1f}%)")
            print(f"\n电池储能系统优化调度已准备就绪！\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
