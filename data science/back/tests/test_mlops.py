
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import joblib

import joblib

# 添加 back 目录到 path (用于导入 services)
# 当前文件在 back/tests/test_mlops.py
# 需要添加 back/ 到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
back_dir = os.path.dirname(current_dir)
# 使用 insert(0, ...) 确保 back 目录在 sys.path 最前，优先于 tests 目录
# 避免 import services 时错误导入 back/tests/services
sys.path.insert(0, back_dir)

# 设置 GCP 凭证 (响应用户输入)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/Users/achilles/Documents/code/data science/service-account-key.json'

from services.ml_service import EnergyPredictor

def create_mock_data(file_path):
    """创建模拟的 CSV 数据"""
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=48)
    dates = pd.date_range(start=start_date, end=end_date, freq='H')
    
    data = {
        'Date': dates,
        'Hour': dates.hour,
        'DayOfWeek': dates.dayofweek,
        # 随机生成一些合理范围的数据
        'Temperature': np.random.uniform(10, 35, len(dates)),
        'Price': np.random.uniform(0.1, 1.5, len(dates)),
        'Site_Load': np.random.uniform(20, 100, len(dates))
    }
    
    df = pd.DataFrame(data)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False)
    print(f"✅ Created mock data at {file_path} with {len(df)} rows")
    return file_path

def create_dummy_model(model_path):
    """创建一个简单的随机森林模型并保存"""
    from sklearn.ensemble import RandomForestRegressor
    
    X = np.random.rand(100, 4) # Hour, DayOfWeek, Temperature, Price
    y = np.random.rand(100) * 100 # Site_Load
    
    model = RandomForestRegressor(n_estimators=10)
    model.fit(X, y)
    
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    print(f"✅ Created dummy model at {model_path}")


def test_mlops():
    print("🚀 Starting MLOps Test...")
    
    # paths (使用 back_dir 确保路径正确)
    data_dir = os.path.join(back_dir, 'data', 'processed')
    models_dir = os.path.join(back_dir, 'models')
    
    mock_data_path = os.path.join(data_dir, 'cleaned_energy_data_all.csv')
    dummy_model_path = os.path.join(models_dir, 'rf_model.joblib')
    
    # 确保模型存在，只创建一次
    if not os.path.exists(dummy_model_path):
        create_dummy_model(dummy_model_path)

    # 场景 1: 正常数据 (Mock data)
    print("\n[Scenario 1] Testing with normal data...")
    create_mock_data(mock_data_path)
    
    run_test_scenario(mock_data_path, dummy_model_path, "Normal Data")

    # 场景 2: 数据缺失/间隔 (Gap)
    # 创建最后 24 小时只有 5 条数据的 CSV
    print("\n[Scenario 2] Testing with data gaps...")
    dates = pd.date_range(end=datetime.now(), periods=50, freq='H')
    # 丢弃中间的数据，制造 gap
    dates_gap = dates[:-30].append(dates[-5:]) 
    
    df_gap = pd.DataFrame({
        'Date': dates_gap,
        'Hour': dates_gap.hour,
        'DayOfWeek': dates_gap.dayofweek,
        'Temperature': np.random.uniform(10, 35, len(dates_gap)),
        'Price': np.random.uniform(0.1, 1.5, len(dates_gap)),
        'Site_Load': np.random.uniform(20, 100, len(dates_gap))
    })
    df_gap.to_csv(mock_data_path, index=False)
    
    run_test_scenario(mock_data_path, dummy_model_path, "Data Gap (Should Fail/Warn)")


def run_test_scenario(data_path, model_path, scenario_name):
    # 2. Mock StorageService
    from unittest.mock import patch
    
    # 我们直接 patch services.storage_service 中的 StorageService 类
    # 这样无论哪里 import 它，都会得到 Mock 对象
    with patch('services.storage_service.StorageService') as MockStorageService:
        # 配置 Mock 实例的行为
        mock_instance = MockStorageService.return_value
        mock_instance.download_to_temp.return_value = data_path
        
        try:
            # 3. 初始化预测器
            predictor = EnergyPredictor(model_path=model_path)
            # 强制加载模型
            import joblib
            predictor.model = joblib.load(model_path)
            
            # 4. 运行评估
            result = predictor.evaluate_recent_performance(hours=24)
            
            print(f"📊 {scenario_name} Result:")
            print(result)
            
            # 验证逻辑
            if scenario_name == "Normal Data":
                if result['status'] == 'success':
                    print("✅ Test PASSED: Normal data handled correctly.")
                else:
                    print(f"❌ Test FAILED: Normal data failed with {result}")
            
            elif scenario_name == "Data Gap (Should Fail/Warn)":
                 # 预期可能是 failure 或 warning (insufficient_data)
                 if result['status'] == 'insufficient_data':
                      print("✅ Test PASSED: Correctly identified insufficient data.")
                 else:
                      print(f"❌ Test FAILED: Should detect insufficient data but got {result['status']}")

        except Exception as e:
            print(f"❌ Test CRASHED in {scenario_name}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_mlops()
