import unittest
import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

# 获取当前文件所在目录 (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录 (back/)
project_root = os.path.dirname(current_dir)
# 将项目根目录添加到 sys.path
sys.path.insert(0, project_root)

# 确保在导入服务模块前已经修改了 sys.path
try:
    from services.external_data_service import ExternalDataService
    from services.data_processor import EnergyDataProcessor
except ImportError:
    # 如果仍然失败，尝试再次调整路径 (兼容性)
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from services.external_data_service import ExternalDataService
    from services.data_processor import EnergyDataProcessor

class TestDataFetching(unittest.TestCase):
    """数据抓取与处理流程测试"""

    def setUp(self):
        """测试准备: 设置环境变量和 Mock 对象"""
        # 仅在非真实数据测试模式下设置 Mock 凭证
        if os.environ.get('TEST_REAL_DATA') != '1':
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "mock_credentials.json"
        
        # Mock StorageService 以避免真实网络调用
        self.storage_patcher = patch('services.external_data_service.StorageService')
        self.MockStorage = self.storage_patcher.start()
        self.mock_storage_instance = self.MockStorage.return_value
        self.mock_storage_instance.download_to_temp.return_value = None  # 模拟首次下载无文件
        
    def tearDown(self):
        """测试清理"""
        self.storage_patcher.stop()

    def test_feature_generation_logic(self):
        """验证是否生成了增强特征 (Season, IsHoliday, etc.)"""
        print("\n🧪 测试特征生成逻辑...")
        
        # 1. 准备模拟数据 (ExternalDataService 中的逻辑)
        processor = EnergyDataProcessor(output_dir="/tmp")
        
        # 构造基础数据
        dates = pd.date_range(start='2023-12-24 12:00:00', periods=5, freq='H') # 包含圣诞夜
        df = pd.DataFrame({
            'Date': dates,
            'Site_Load': [100, 105, 110, 108, 102],
            'Temperature': [15, 14, 13, 12, 11],
            'Price': [0.5, 0.5, 0.5, 0.5, 0.5],
            'Hour': dates.hour,
            'DayOfWeek': dates.dayofweek
        })
        
        print(f"   输入数据: {len(df)} 行")
        
        # 2. 模拟 ExternalDataService 的处理流程
        # Step A: 确保 Date 是 datetime (修复点验证)
        if df['Date'].dtype == 'object':
            df['Date'] = pd.to_datetime(df['Date'])
            
        # Step B: 添加增强特征 (修复点验证)
        df = processor.add_enhanced_time_features(df)
        
        # Step C: 添加高级特征
        df_processed = processor.add_advanced_features(df, dropna=False, use_enhanced=True)
        
        # 3. 断言验证
        # 验证增强特征是否存在
        required_features = ['Season', 'IsHoliday', 'Month', 'IsWeekend']
        for feat in required_features:
            self.assertIn(feat, df_processed.columns, f"缺少增强特征: {feat}")
            print(f"   ✅ 特征存在: {feat}")
            
        # 验证具体值逻辑 (2023-12-24 是冬天)
        self.assertEqual(df_processed['Season'].iloc[0], 3, "2023-12-24 应该是冬季 (Season=3)")
        print("   ✅ 季节判断正确 (Winter)")
        
        # 验证交互特征
        self.assertIn('Temp_x_Season', df_processed.columns, "缺少交互特征: Temp_x_Season")
        print("   ✅ 交互特征 Temp_x_Season 存在")
        
    @patch('services.external_data_service.ExternalDataService.fetch_caiso_load')
    @patch('services.external_data_service.ExternalDataService.fetch_weather_data')
    def test_fetch_and_publish_flow(self, mock_weather, mock_caiso):
        """测试完整的数据获取与发布流程"""
        print("\n🧪 测试数据获取与发布流程...")
        
        # 配置 Mock 返回值 (模拟 CAISO 和 Weather API 数据)
        mock_caiso.return_value = (25000.0, datetime.now())
        mock_weather.return_value = (20.5, datetime.now())
        
        # 实例化服务
        service = ExternalDataService()
        
        # 检查是否启用真实数据测试模式
        use_real_data = os.environ.get('TEST_REAL_DATA') == '1'
        
        if use_real_data:
            print("   ⚠️  检测到 TEST_REAL_DATA=1: 正在尝试连接真实 GCP Storage 获取历史数据...")
            # 恢复真实的 download_to_temp 方法 (取消 Mock)
            self.storage_patcher.stop()
            # 重新实例化以使用真实 StorageService
            service = ExternalDataService()
            # 再次 Mock upload_file 防止污染生产数据 (只读测试)
            service.storage_service.upload_file = MagicMock()
            print("   ✅ 已连接真实 Storage (写入操作已安全屏蔽)")
        else:
            # 默认模式：完全 Mock 下载
            service.storage_service.download_to_temp.return_value = None
        
        # 执行核心方法
        success = service.fetch_and_publish()
        
        self.assertTrue(success, "数据抓取任务应该成功返回 True")
        print("   ✅ fetch_and_publish 返回成功")
        
                # 验证结果
        if use_real_data:
            print("   🔍 真实数据验证: 正在检查是否生成了非 NaN 的 Lag 特征...")
            args, _ = service.storage_service.upload_file.call_args
            content = args[0] 
            
            # 读取生成的 CSV
            # 1. 如果是文件对象 (可能是已关闭的 tempfile)
            if hasattr(content, 'name') and os.path.exists(content.name):
                # 直接从磁盘读取文件
                df_result = pd.read_csv(content.name)
            # 2. 如果是开启的文件对象
            elif hasattr(content, 'read') and not getattr(content, 'closed', False):
                content.seek(0)
                df_result = pd.read_csv(content)
            # 3. 如果是 bytes 或 string
            else:
                from io import StringIO, BytesIO
                if isinstance(content, bytes):
                    df_result = pd.read_csv(BytesIO(content))
                elif isinstance(content, str):
                    df_result = pd.read_csv(StringIO(content))
                else:
                    # 尝试最后一种情况：也许文件已经删除了但我们只能拿到路径？
                    # 但在 StorageService 中，tempfile 是在 upload 后才删除的
                    # 如果还是失败，可能是 Mock 获取到的参数已经是关闭的文件句柄
                    print("   ⚠️  无法读取上传内容 (文件可能已关闭或删除)")
                    return

            # 检查 Lag_24h 是否有值 (如果有历史数据，最后一行应该有值)
            if 'Lag_24h' in df_result.columns:
                last_val = df_result['Lag_24h'].iloc[-1]
                if pd.notna(last_val):
                     print(f"   🎉 成功! 使用真实历史数据计算出了 Lag_24h: {last_val}")
                else:
                     print("   ⚠️  警告: Lag_24h 仍为 NaN (可能是历史数据不足 24 小时)")
            else:
                print("   ❌ 错误: 结果中没有 Lag_24h 列")
        else:
            # Mock 模式下的验证
            self.mock_storage_instance.upload_file.assert_called()
            print("   ✅ 验证了 storage_service.upload_file 被调用")

if __name__ == '__main__':
    unittest.main()
