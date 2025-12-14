"""
ML服务内部测试脚本
提取自 ml_service.py 的 main 函数
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
# 添加 back 目录到路径，以便 services 模块可以被直接导入
sys.path.insert(0, str(project_root / 'back'))

from back.services.ml_service import EnergyPredictor

def main():
    """
    主函数 - 测试代码
    """
    print("\n" + "🎯 " + "="*76)
    print("能源负载预测系统 - 测试脚本")
    print("="*78 + "\n")
    
    # 1. 实例化预测器
    print("【步骤 1】实例化 EnergyPredictor")
    print("-" * 80)
    predictor = EnergyPredictor()
    
    # 2. 训练模型
    print("\n【步骤 2】训练模型")
    print("-" * 80)
    try:
        metrics = predictor.train_model(n_estimators=100)
    except Exception as e:
        print(f"⚠️ 训练失败 (可能是本地没有数据): {e}")
        print("尝试直接加载已有模型...")
    
    # 3. 测试加载模型
    print("\n【步骤 3】测试加载模型")
    print("-" * 80)
    predictor_new = EnergyPredictor()
    try:
        predictor_new.load_model()
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return 1
    
    # 4. 预测未来24小时
    print("\n【步骤 4】预测未来24小时负载")
    print("-" * 80)
    
    # 使用明天的日期
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    # 模拟温度预测（夏季温度模式）
    temp_forecast = [
        24.0, 23.5, 23.0, 22.8, 22.5, 23.0,  # 00:00-05:00 (夜间降温)
        24.0, 25.0, 26.5, 28.0, 29.5, 30.5,  # 06:00-11:00 (升温)
        31.0, 31.5, 31.8, 31.5, 31.0, 30.0,  # 12:00-17:00 (高温)
        28.5, 27.0, 26.0, 25.5, 25.0, 24.5   # 18:00-23:00 (降温)
    ]
    
    predictions = predictor_new.predict_next_24h(
        start_time=tomorrow,
        temp_forecast_list=temp_forecast
    )
    
    # 5. 显示预测结果
    print("\n【步骤 5】预测结果展示")
    print("-" * 80)
    print(f"\n预测日期: {tomorrow.strftime('%Y-%m-%d')}\n")
    print(f"{'时间':<12} {'预测负载':<12} {'温度':<10} {'电价':<10} {'时段':<10}")
    print("-" * 80)
    
    for pred in predictions[:12]:  # 只显示前12小时
        dt = pred['datetime']
        load = pred['predicted_load']
        temp = pred['temperature']
        price = pred['price']
        
        # 判断时段
        if price == 0.3:
            period = "谷时"
        elif price == 0.6:
            period = "平时"
        else:
            period = "峰时"
        
        print(f"{dt.strftime('%H:%M'):<12} {load:>8.2f} kW  {temp:>6.1f}°C  {price:>6.2f}元  {period:<10}")
    
    print("... (后12小时省略)")
    
    # 6. 单点预测测试
    print("\n【步骤 6】单点预测测试")
    print("-" * 80)
    
    test_cases = [
        (0, 1, 24.0, "周一凌晨0点，24°C"),
        (12, 1, 30.0, "周一中午12点，30°C"),
        (20, 1, 28.0, "周一晚上8点，28°C"),
    ]
    
    try:
        for hour, dow, temp, desc in test_cases:
            # 注意: predict_single 已被废弃，这里可能抛出异常，需捕获
            try:
                pred = predictor_new.predict_single(hour, dow, temp)
                print(f"   {desc}: {pred:.2f} kW")
            except NotImplementedError:
                print(f"   {desc}: (API 已废弃)")
    except Exception as e:
        print(f"   单点预测测试跳过: {e}")
    
    # 7. 总结
    print("\n" + "="*80)
    print("✅ 测试完成!")
    print("="*80)
    if 'metrics' in locals() and metrics:
        print(f"\n模型性能:")
        print(f"   - 测试集 MAE:  {metrics.get('test_mae', 0):.2f} kW")
        print(f"   - 测试集 RMSE: {metrics.get('test_rmse', 0):.2f} kW")
    
    print(f"\n模型已保存到: {predictor.local_model_path}")
    print(f"可以通过 load_model() 加载使用\n")


if __name__ == "__main__":
    main()
