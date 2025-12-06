"""
优化服务单元测试
Unit tests for optimization_service.py

测试 EnergyOptimizer 类的核心功能和边界条件
"""

import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestEnergyOptimizerInit:
    """测试 EnergyOptimizer 初始化"""
    
    @pytest.mark.unit
    def test_default_parameters(self):
        """测试默认参数初始化"""
        from services.optimization_service import EnergyOptimizer, GUROBI_AVAILABLE
        
        if not GUROBI_AVAILABLE:
            pytest.skip("Gurobi 不可用，跳过此测试")
        
        optimizer = EnergyOptimizer()
        
        assert optimizer.battery_capacity == 13.5, "默认电池容量应为 13.5 kWh"
        assert optimizer.max_power == 5.0, "默认最大功率应为 5.0 kW"
        assert optimizer.efficiency == 0.95, "默认效率应为 0.95"
    
    @pytest.mark.unit
    def test_custom_parameters(self):
        """测试自定义参数初始化"""
        from services.optimization_service import EnergyOptimizer, GUROBI_AVAILABLE
        
        if not GUROBI_AVAILABLE:
            pytest.skip("Gurobi 不可用，跳过此测试")
        
        optimizer = EnergyOptimizer(
            battery_capacity=20.0,
            max_power=10.0,
            efficiency=0.90
        )
        
        assert optimizer.battery_capacity == 20.0
        assert optimizer.max_power == 10.0
        assert optimizer.efficiency == 0.90


class TestOptimizeSchedule:
    """测试优化调度功能"""
    
    @pytest.fixture
    def optimizer(self):
        """创建优化器实例"""
        from services.optimization_service import GUROBI_AVAILABLE
        if not GUROBI_AVAILABLE:
            pytest.skip("Gurobi 不可用，跳过此测试")
        
        from services.optimization_service import EnergyOptimizer
        return EnergyOptimizer(battery_capacity=13.5, max_power=5.0, efficiency=0.95)
    
    @pytest.fixture
    def sample_profiles(self):
        """示例负载和电价配置"""
        # 24小时负载数据 (kW)
        load_profile = [
            3.0, 2.5, 2.0, 2.0, 2.5, 3.0,  # 00:00-05:00 (夜间低负载)
            4.0, 5.0, 6.0, 7.0, 8.0, 8.5,  # 06:00-11:00 (上午增长)
            8.0, 7.5, 7.0, 6.5, 6.0, 7.0,  # 12:00-17:00 (下午平稳)
            9.0, 10.0, 9.5, 8.0, 5.0, 4.0  # 18:00-23:00 (晚高峰)
        ]
        # 24小时电价 (元/kWh) - 峰谷电价
        price_profile = [
            0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3,  # 00:00-07:00 (谷时)
            0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6,  # 08:00-15:00 (平时)
            0.6, 0.6, 1.0, 1.0, 1.0, 1.0, 0.3, 0.3   # 16:00-23:00 (混合)
        ]
        return load_profile, price_profile
    
    @pytest.mark.unit
    def test_optimize_returns_valid_result(self, optimizer, sample_profiles):
        """测试优化返回有效结果"""
        load_profile, price_profile = sample_profiles
        
        result = optimizer.optimize_schedule(
            load_profile=load_profile,
            price_profile=price_profile,
            initial_soc=0.5
        )
        
        assert result is not None, "结果不应为 None"
        assert 'status' in result, "结果应包含 status"
        assert 'schedule' in result, "结果应包含 schedule"
        assert 'total_cost_with_battery' in result, "结果应包含成本信息"
    
    @pytest.mark.unit
    def test_schedule_length_matches_input(self, optimizer, sample_profiles):
        """测试调度长度匹配输入"""
        load_profile, price_profile = sample_profiles
        
        result = optimizer.optimize_schedule(
            load_profile=load_profile,
            price_profile=price_profile,
            initial_soc=0.5
        )
        
        assert len(result['schedule']) == 24, "调度结果应有24个时间点"
    
    @pytest.mark.unit
    def test_savings_non_negative(self, optimizer, sample_profiles):
        """测试节省金额非负"""
        load_profile, price_profile = sample_profiles
        
        result = optimizer.optimize_schedule(
            load_profile=load_profile,
            price_profile=price_profile,
            initial_soc=0.5
        )
        
        if result['status'] == 'Optimal':
            assert result['savings'] >= 0, "节省金额应为非负"
            assert result['total_cost_with_battery'] <= result['total_cost_without_battery'], \
                "有电池的成本应低于或等于无电池成本"


class TestEdgeCases:
    """测试边界条件"""
    
    @pytest.fixture
    def optimizer(self):
        """创建优化器实例"""
        from services.optimization_service import GUROBI_AVAILABLE
        if not GUROBI_AVAILABLE:
            pytest.skip("Gurobi 不可用，跳过此测试")
        
        from services.optimization_service import EnergyOptimizer
        return EnergyOptimizer()
    
    @pytest.mark.unit
    def test_empty_load_profile(self, optimizer):
        """测试空负载列表"""
        with pytest.raises((ValueError, Exception)):
            optimizer.optimize_schedule(
                load_profile=[],
                price_profile=[],
                initial_soc=0.5
            )
    
    @pytest.mark.unit
    def test_mismatched_profile_lengths(self, optimizer):
        """测试不匹配的配置长度"""
        with pytest.raises((ValueError, Exception)):
            optimizer.optimize_schedule(
                load_profile=[1.0] * 24,
                price_profile=[0.5] * 12,  # 长度不匹配
                initial_soc=0.5
            )
    
    @pytest.mark.unit
    def test_invalid_soc_value(self, optimizer):
        """测试无效的初始电量值"""
        with pytest.raises((ValueError, Exception)):
            optimizer.optimize_schedule(
                load_profile=[5.0] * 24,
                price_profile=[0.6] * 24,
                initial_soc=1.5  # 超出范围
            )
    
    @pytest.mark.unit
    def test_zero_load_profile(self, optimizer):
        """测试全零负载"""
        result = optimizer.optimize_schedule(
            load_profile=[0.0] * 24,
            price_profile=[0.6] * 24,
            initial_soc=0.5
        )
        
        # 即使负载为零，也应返回有效结果
        assert result is not None
        assert result['total_cost_without_battery'] == 0.0, "零负载时无电池成本应为 0"


class TestGurobiUnavailable:
    """测试 Gurobi 不可用时的行为"""
    
    @pytest.mark.unit
    def test_gurobi_flag_exists(self):
        """测试 GUROBI_AVAILABLE 标志存在"""
        from services.optimization_service import GUROBI_AVAILABLE
        
        assert isinstance(GUROBI_AVAILABLE, bool), "GUROBI_AVAILABLE 应为布尔值"
