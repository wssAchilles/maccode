"""
直接测试优化功能（不通过 API）
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from back.services.ml_service import EnergyPredictor
from back.services.optimization_service import EnergyOptimizer


def test_optimization_workflow():
    """测试完整的优化工作流程"""
    print("\n" + "="*80)
    print("🧪 测试优化工作流程（直接调用）")
    print("="*80 + "\n")
    
    try:
        # 步骤 1: 负载预测
        print("【步骤 1】负载预测")
        print("-" * 80)
        
        predictor = EnergyPredictor()
        predictor.load_model()
        
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        temp_forecast = [
            24.0, 23.5, 23.0, 22.8, 22.5, 23.0,
            24.0, 25.0, 26.5, 28.0, 29.5, 30.5,
            31.0, 31.5, 31.8, 31.5, 31.0, 30.0,
            28.5, 27.0, 26.0, 25.5, 25.0, 24.5
        ]
        
        predictions = predictor.predict_next_24h(
            start_time=tomorrow,
            temp_forecast_list=temp_forecast
        )
        
        load_profile = [p['predicted_load'] for p in predictions]
        price_profile = [p['price'] for p in predictions]
        
        print(f"✅ 预测完成: {len(predictions)} 小时")
        print(f"   负载范围: {min(load_profile):.2f} - {max(load_profile):.2f} kW")
        
        # 步骤 2: 优化调度
        print("\n【步骤 2】优化调度")
        print("-" * 80)
        
        optimizer = EnergyOptimizer(
            battery_capacity=13.5,
            max_power=5.0,
            efficiency=0.95
        )
        
        result = optimizer.optimize_schedule(
            load_profile=load_profile,
            price_profile=price_profile,
            initial_soc=0.5
        )
        
        # 步骤 3: 显示结果
        print("\n【步骤 3】优化结果")
        print("-" * 80)
        
        if result['status'] == 'Optimal':
            print(f"✅ 优化成功!")
            print(f"\n成本分析:")
            print(f"   - 无电池成本: {result['total_cost_without_battery']:.2f} 元")
            print(f"   - 有电池成本: {result['total_cost_with_battery']:.2f} 元")
            print(f"   - 节省金额: {result['savings']:.2f} 元")
            print(f"   - 节省比例: {result['savings_percent']:.1f}%")
            
            schedule = result['schedule']
            
            # 充放电策略
            charging_hours = [s for s in schedule if s['battery_action'] > 0.01]
            discharging_hours = [s for s in schedule if s['battery_action'] < -0.01]
            
            print(f"\n充放电策略:")
            print(f"   - 充电时段: {len(charging_hours)} 小时")
            for s in charging_hours:
                print(f"      {s['hour']:02d}:00 - 充电 {s['charge_power']:.2f} kW @ {s['price']:.2f}元")
            
            print(f"   - 放电时段: {len(discharging_hours)} 小时")
            for s in discharging_hours:
                print(f"      {s['hour']:02d}:00 - 放电 {s['discharge_power']:.2f} kW @ {s['price']:.2f}元")
            
            # 模拟 API 响应格式
            print(f"\n【步骤 4】API 响应格式示例")
            print("-" * 80)
            
            import json
            
            # 构建图表数据
            chart_data = []
            for item in schedule[:5]:  # 只显示前5小时
                dt = tomorrow + timedelta(hours=item['hour'])
                chart_data.append({
                    'hour': item['hour'],
                    'datetime': dt.strftime('%Y-%m-%dT%H:%M:%S'),
                    'load': round(item['load'], 2),
                    'price': item['price'],
                    'battery_action': round(item['battery_action'], 2),
                    'soc': round(item['soc'] * 100, 1),
                    'grid_power': round(item['load'] + item['battery_action'], 2)
                })
            
            api_response = {
                'success': True,
                'optimization': {
                    'status': 'Optimal',
                    'chart_data': chart_data,
                    'summary': {
                        'total_cost_without_battery': round(result['total_cost_without_battery'], 2),
                        'total_cost_with_battery': round(result['total_cost_with_battery'], 2),
                        'savings': round(result['savings'], 2),
                        'savings_percent': round(result['savings_percent'], 2)
                    }
                }
            }
            
            print(json.dumps(api_response, indent=2, ensure_ascii=False))
            
            print("\n" + "="*80)
            print("✅ 测试完成!")
            print("="*80)
            
            return True
        else:
            print(f"❌ 优化失败: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_optimization_workflow()
    sys.exit(0 if success else 1)
