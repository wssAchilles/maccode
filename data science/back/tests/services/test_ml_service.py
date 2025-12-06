"""
机器学习服务单元测试
Pytest style unit tests for ml_service.py

测试 EnergyPredictor 类的核心功能
"""

import sys
from pathlib import Path
import pytest
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.ml_service import EnergyPredictor


class TestEnergyPredictorInit:
    """测试 EnergyPredictor 初始化"""
    
    @pytest.mark.unit
    def test_init_creates_instance(self):
        """测试实例创建"""
        predictor = EnergyPredictor()
        assert predictor is not None
        assert predictor.model is None, "初始化时模型应为 None"


class TestModelLoading:
    """测试模型加载功能"""
    
    @pytest.fixture
    def predictor(self):
        """创建预测器实例"""
        return EnergyPredictor()
    
    @pytest.mark.unit
    @pytest.mark.slow
    def test_load_model_success(self, predictor):
        """测试模型加载成功"""
        success = predictor.load_model()
        
        assert success is True, "模型加载应成功"
        assert predictor.model is not None, "加载后模型不应为 None"


class TestPrediction:
    """测试预测功能"""
    
    @pytest.fixture
    def loaded_predictor(self):
        """创建并加载模型的预测器"""
        predictor = EnergyPredictor()
        predictor.load_model()
        return predictor
    
    @pytest.mark.unit
    def test_predict_next_24h_returns_24_items(self, loaded_predictor):
        """测试24小时预测返回24个结果"""
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        predictions = loaded_predictor.predict_next_24h(start_time=tomorrow)
        
        assert len(predictions) == 24, "应返回24个预测结果"
    
    @pytest.mark.unit
    def test_predict_next_24h_contains_required_fields(self, loaded_predictor):
        """测试预测结果包含必需字段"""
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        predictions = loaded_predictor.predict_next_24h(start_time=tomorrow)
        
        for pred in predictions:
            assert 'datetime' in pred, "应包含 datetime"
            assert 'predicted_load' in pred, "应包含 predicted_load"
            assert 'price' in pred, "应包含 price"
    
    @pytest.mark.unit
    def test_predict_next_24h_with_temperature(self, loaded_predictor):
        """测试带温度预测"""
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        temp_forecast = [25.0 + i * 0.5 for i in range(24)]
        
        predictions = loaded_predictor.predict_next_24h(
            start_time=tomorrow,
            temp_forecast_list=temp_forecast
        )
        
        assert len(predictions) == 24
    
    @pytest.mark.unit
    def test_predict_single_returns_positive(self, loaded_predictor):
        """测试单点预测返回正值"""
        load = loaded_predictor.predict_single(
            hour=12,
            day_of_week=0,
            temperature=25.0
        )
        
        assert load > 0, "预测负载应为正数"


class TestPredictionEdgeCases:
    """测试预测边界条件"""
    
    @pytest.fixture
    def predictor(self):
        """创建预测器实例"""
        return EnergyPredictor()
    
    @pytest.fixture
    def loaded_predictor(self, predictor):
        """加载模型"""
        predictor.load_model()
        return predictor
    
    @pytest.mark.unit
    def test_predict_without_loading_raises_error(self, predictor):
        """测试未加载模型时预测抛出错误"""
        with pytest.raises(ValueError):
            predictor.predict_next_24h(start_time=datetime.now())
    
    @pytest.mark.unit
    def test_predict_with_wrong_temp_length_raises_error(self, loaded_predictor):
        """测试错误长度的温度列表抛出错误"""
        with pytest.raises(ValueError):
            loaded_predictor.predict_next_24h(
                start_time=datetime.now(),
                temp_forecast_list=[25.0] * 10  # 应为24个
            )


class TestPriceCalculation:
    """测试电价计算"""
    
    @pytest.fixture
    def predictor(self):
        return EnergyPredictor()
    
    @pytest.mark.unit
    def test_valley_hours_price(self, predictor):
        """测试谷时电价"""
        # 凌晨0点应为谷时
        price = predictor._get_price(0)
        assert price == 0.3, "凌晨应为谷时电价 0.3"
    
    @pytest.mark.unit
    def test_peak_hours_price(self, predictor):
        """测试峰时电价"""
        # 晚上7点应为峰时
        price = predictor._get_price(19)
        assert price == 1.0, "晚间应为峰时电价 1.0"
    
    @pytest.mark.unit
    def test_normal_hours_price(self, predictor):
        """测试平时电价"""
        # 上午10点应为平时
        price = predictor._get_price(10)
        assert price == 0.6, "上午应为平时电价 0.6"
