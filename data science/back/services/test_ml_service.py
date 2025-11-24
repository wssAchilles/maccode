"""
机器学习服务测试脚本
Test script for ML service
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from back.services.ml_service import EnergyPredictor


def test_model_training():
    """测试模型训练"""
    print("\n" + "="*80)
    print("测试 1: 模型训练")
    print("="*80)
    
    predictor = EnergyPredictor()
    metrics = predictor.train_model(n_estimators=50)  # 使用较少的树以加快测试
    
    assert metrics['test_mae'] > 0, "MAE 应该大于 0"
    assert metrics['test_rmse'] > 0, "RMSE 应该大于 0"
    assert predictor.model is not None, "模型应该已训练"
    
    print("✅ 模型训练测试通过")
    return predictor


def test_model_loading():
    """测试模型加载"""
    print("\n" + "="*80)
    print("测试 2: 模型加载")
    print("="*80)
    
    predictor = EnergyPredictor()
    success = predictor.load_model()
    
    assert success, "模型加载应该成功"
    assert predictor.model is not None, "模型应该已加载"
    
    print("✅ 模型加载测试通过")
    return predictor


def test_24h_prediction(predictor):
    """测试24小时预测"""
    print("\n" + "="*80)
    print("测试 3: 24小时预测")
    print("="*80)
    
    # 使用明天作为开始时间
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    # 测试1: 不提供温度预测
    predictions = predictor.predict_next_24h(start_time=tomorrow)
    
    assert len(predictions) == 24, "应该返回24个预测结果"
    assert all('datetime' in p for p in predictions), "每个预测应包含 datetime"
    assert all('predicted_load' in p for p in predictions), "每个预测应包含 predicted_load"
    
    print(f"✓ 预测结果数量正确: {len(predictions)}")
    
    # 测试2: 提供温度预测
    temp_forecast = [25.0 + i * 0.5 for i in range(24)]  # 简单的温度模式
    predictions_with_temp = predictor.predict_next_24h(
        start_time=tomorrow,
        temp_forecast_list=temp_forecast
    )
    
    assert len(predictions_with_temp) == 24, "应该返回24个预测结果"
    
    print("✓ 带温度预测的预测正常")
    print("✅ 24小时预测测试通过")
    
    return predictions


def test_single_prediction(predictor):
    """测试单点预测"""
    print("\n" + "="*80)
    print("测试 4: 单点预测")
    print("="*80)
    
    # 测试不同时段的预测
    test_cases = [
        (0, 0, 25.0, "周一凌晨"),
        (12, 0, 30.0, "周一中午"),
        (20, 0, 28.0, "周一晚上"),
        (12, 5, 30.0, "周六中午"),
    ]
    
    for hour, dow, temp, desc in test_cases:
        load = predictor.predict_single(hour, dow, temp)
        assert load > 0, f"{desc} 的预测负载应该大于 0"
        print(f"✓ {desc} ({hour}:00, 温度{temp}°C): {load:.2f} kW")
    
    print("✅ 单点预测测试通过")


def test_prediction_analysis(predictions):
    """测试预测结果分析"""
    print("\n" + "="*80)
    print("测试 5: 预测结果分析")
    print("="*80)
    
    # 转换为 DataFrame
    df = pd.DataFrame(predictions)
    
    # 统计分析
    print(f"\n负载统计:")
    print(f"  - 平均: {df['predicted_load'].mean():.2f} kW")
    print(f"  - 最大: {df['predicted_load'].max():.2f} kW")
    print(f"  - 最小: {df['predicted_load'].min():.2f} kW")
    print(f"  - 标准差: {df['predicted_load'].std():.2f} kW")
    
    # 按电价分组
    print(f"\n按电价分组:")
    price_groups = df.groupby('price')['predicted_load'].agg(['mean', 'count'])
    for price, row in price_groups.iterrows():
        period = "谷时" if price == 0.3 else ("平时" if price == 0.6 else "峰时")
        print(f"  - {period} ({price}元): 平均 {row['mean']:.2f} kW, {int(row['count'])} 小时")
    
    # 找出峰值时刻
    peak_idx = df['predicted_load'].idxmax()
    peak_time = df.loc[peak_idx, 'datetime']
    peak_load = df.loc[peak_idx, 'predicted_load']
    print(f"\n峰值负载:")
    print(f"  - 时刻: {peak_time.strftime('%H:%M')}")
    print(f"  - 负载: {peak_load:.2f} kW")
    
    print("\n✅ 预测结果分析测试通过")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*80)
    print("测试 6: 错误处理")
    print("="*80)
    
    predictor = EnergyPredictor()
    
    # 测试未加载模型时预测
    try:
        predictor.predict_next_24h(start_time=datetime.now())
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        print(f"✓ 正确捕获未加载模型错误: {str(e)[:50]}...")
    
    # 加载模型
    predictor.load_model()
    
    # 测试错误的温度列表长度
    try:
        predictor.predict_next_24h(
            start_time=datetime.now(),
            temp_forecast_list=[25.0] * 10  # 错误的长度
        )
        assert False, "应该抛出 ValueError"
    except ValueError as e:
        print(f"✓ 正确捕获温度列表长度错误: {str(e)[:50]}...")
    
    print("✅ 错误处理测试通过")


def main():
    """主测试函数"""
    print("\n" + "🧪 " + "="*76)
    print("机器学习服务测试套件")
    print("="*78)
    
    try:
        # 1. 训练模型（如果需要）
        predictor = test_model_training()
        
        # 2. 测试加载模型
        predictor = test_model_loading()
        
        # 3. 测试24小时预测
        predictions = test_24h_prediction(predictor)
        
        # 4. 测试单点预测
        test_single_prediction(predictor)
        
        # 5. 测试预测结果分析
        test_prediction_analysis(predictions)
        
        # 6. 测试错误处理
        test_error_handling()
        
        # 总结
        print("\n" + "="*80)
        print("🎉 所有测试通过!")
        print("="*80)
        print("\n机器学习服务已准备就绪，可以集成到 API 中使用。\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
