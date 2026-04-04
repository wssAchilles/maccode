"""
外部数据服务 - CAISO 电网数据 & OpenWeatherMap 天气数据
External Data Service for CAISO Grid Data and Weather Information

此服务负责:
1. 从 CAISO (California ISO) 获取实时电力负载数据
2. 从 OpenWeatherMap 获取洛杉矶的实时天气数据
3. 数据对齐和时区处理
4. 持久化到 Firebase Storage
"""

import os
import requests
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
import pytz
import gridstatus
from services.storage_service import StorageService
from services.data_processor import EnergyDataProcessor
from services.secrets import get_secret


class ExternalDataService:
    """外部数据获取服务"""
    
    def __init__(self):
        """初始化服务"""
        try:
            self.storage_service = StorageService()
        except EnvironmentError as e:
            raise EnvironmentError(
                "StorageService 初始化失败: 未检测到本地 GCP 凭证，请设置 GOOGLE_APPLICATION_CREDENTIALS 或 GCP_SERVICE_ACCOUNT_JSON 后重试。\n"
                f"原始错误: {e}"
            )
        
        # OpenWeather API 配置（使用 secrets 模块统一管理敏感密钥）
        self.weather_api_key = get_secret('OPENWEATHER_API_KEY')
        self.weather_lat = float(os.getenv('WEATHER_CITY_LAT', '34.05'))  # Los Angeles
        self.weather_lon = float(os.getenv('WEATHER_CITY_LON', '-118.24'))
        self.weather_api_url = 'https://api.openweathermap.org/data/2.5/weather'
        
        # CAISO ISO 客户端
        self.caiso_client = None
        
        # 数据存储路径
        self.csv_file_path = 'data/processed/cleaned_energy_data_all.csv'
        
        print("✓ ExternalDataService 初始化完成")
    
    def _get_caiso_client(self):
        """
        获取 CAISO 客户端 (延迟初始化)
        
        Returns:
            gridstatus.CAISO: CAISO 客户端实例
        """
        if self.caiso_client is None:
            try:
                self.caiso_client = gridstatus.CAISO()
                print("✓ CAISO 客户端初始化成功")
            except Exception as e:
                print(f"❌ CAISO 客户端初始化失败: {str(e)}")
                raise
        return self.caiso_client
    
    def fetch_caiso_load(self) -> Tuple[Optional[float], Optional[datetime]]:
        """
        获取 CAISO 最新的电力负载数据
        
        Returns:
            Tuple[float, datetime]: (负载值 MW, 时间戳 UTC)
            如果失败返回 (None, None)
        """
        try:
            print("\n🔌 获取 CAISO 电力负载数据...")
            
            # 使用加州时间确定日期，避免 UTC 时间导致的 404 错误
            # GAE 服务器使用 UTC，但 CAISO 数据按加州时间发布
            pacific_tz = pytz.timezone('America/Los_Angeles')
            now_pacific = datetime.now(pacific_tz)
            date_str = now_pacific.strftime('%Y-%m-%d')
            
            print(f"   - 服务器 UTC 时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   - 加州 PST/PDT 时间: {now_pacific.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print(f"   - 请求日期: {date_str}")
            
            # 获取指定日期的负载数据
            iso = self._get_caiso_client()
            df = iso.get_load(date=date_str)
            
            if df is None or len(df) == 0:
                print("   ⚠️  未获取到 CAISO 数据")
                return None, None
            
            # 提取最后一行 (最新数据)
            latest_row = df.iloc[-1]
            
            # 获取负载值 (可能的列名: 'Load', 'load', 'Load_MW')
            load_value = None
            for col in ['Load', 'load', 'Load_MW', 'LOAD']:
                if col in latest_row.index:
                    load_value = float(latest_row[col])
                    break
            
            if load_value is None:
                print(f"   ⚠️  未找到负载列，可用列: {list(df.columns)}")
                return None, None
            
            # 获取时间戳 (可能的列名: 'Time', 'time', 'Datetime', 'datetime')
            timestamp = None
            for col in ['Time', 'time', 'Datetime', 'datetime', 'Interval Start', 'interval_start']:
                if col in latest_row.index:
                    timestamp = latest_row[col]
                    break
            
            if timestamp is None:
                print(f"   ⚠️  未找到时间列，使用当前时间")
                timestamp = datetime.now(timezone.utc)
            
            # 时区处理: 转换为 UTC naive datetime
            if isinstance(timestamp, pd.Timestamp):
                if timestamp.tz is not None:
                    # 有时区信息，转换为 UTC 后移除时区
                    timestamp = timestamp.tz_convert(timezone.utc).replace(tzinfo=None)
                else:
                    # 无时区信息，假设为 UTC
                    timestamp = timestamp.to_pydatetime()
            elif isinstance(timestamp, datetime):
                if timestamp.tzinfo is not None:
                    # 有时区信息，转换为 UTC 后移除时区
                    timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                # 字符串或其他格式，尝试解析
                timestamp = pd.to_datetime(timestamp)
                if timestamp.tz is not None:
                    timestamp = timestamp.tz_convert(timezone.utc).replace(tzinfo=None)
                else:
                    timestamp = timestamp.to_pydatetime()
            
            # ====================================================================
            # 关键修复: 数据量级缩放 (Scaling)
            # CAISO 数据单位为 MW (峰值约 40GW = 40,000MW)
            # 家庭/微网数据单位为 kW (峰值约 200kW)
            # 为了演示效果，我们将电网数据"微缩"到微网规模，保留其波动形状
            # ====================================================================
            
            # 使用固定比例进行缩放，参考峰值: 40000 MW -> 200 kW
            # 比例 = 200 / 40000 = 0.005
            MW_TO_KW_SCALE_FACTOR = 200.0 / 40000.0 
            
            # 执行转换: MW -> 缩放后的 kW
            load_kw = load_value * MW_TO_KW_SCALE_FACTOR
            
            print(f"   ✓ CAISO 原始负载: {load_value:.2f} MW")
            print(f"   ✓ 缩放后微网负载: {load_kw:.2f} kW (Scaling Factor: {MW_TO_KW_SCALE_FACTOR:.6f})")
            print(f"   ✓ 时间戳: {timestamp} (UTC)")
            
            return load_kw, timestamp
            
        except Exception as e:
            print(f"   ❌ 获取 CAISO 数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def fetch_weather_data(self) -> Tuple[Optional[float], Optional[datetime]]:
        """
        获取洛杉矶的当前天气数据
        
        Returns:
            Tuple[float, datetime]: (温度 °C, 时间戳 UTC)
            如果失败返回 (None, None)
        """
        try:
            print("\n🌤️  获取天气数据 (Los Angeles)...")
            
            if not self.weather_api_key:
                print("   ⚠️  未配置 OPENWEATHER_API_KEY")
                return None, None
            
            # 调用 OpenWeather API
            params = {
                'lat': self.weather_lat,
                'lon': self.weather_lon,
                'appid': self.weather_api_key,
                'units': 'metric'  # 使用摄氏度
            }
            
            response = requests.get(self.weather_api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 提取温度
            temperature = data['main']['temp']
            
            # 提取时间戳 (UTC)
            timestamp_unix = data['dt']
            timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc).replace(tzinfo=None)
            
            print(f"   ✓ 温度: {temperature:.1f}°C")
            print(f"   ✓ 时间戳: {timestamp} (UTC)")
            
            return temperature, timestamp
            
        except requests.exceptions.RequestException as e:
            print(f"   ❌ 天气 API 请求失败: {str(e)}")
            return None, None
        except Exception as e:
            print(f"   ❌ 获取天气数据失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def _get_price_by_hour(self, hour: int) -> float:
        """
        根据小时返回简化的峰谷电价
        
        Args:
            hour: 小时 (0-23)
            
        Returns:
            电价 (元/kWh)
        """
        if 8 <= hour < 18:
            return 0.6  # 平时
        elif 18 <= hour < 22:
            return 1.0  # 峰时
        else:
            return 0.3  # 谷时
    
    def fetch_and_publish(self) -> bool:
        """
        核心方法: 获取最新数据并发布到 Firebase Storage
        
        执行流程:
        1. 获取 CAISO 电力负载
        2. 获取 OpenWeather 天气数据
        3. 构造原始数据行
        4. 从 Storage 下载已有 CSV
        5. 追加新行
        6. **实时计算高级特征** (Lag/Rolling)
        7. 保存全量数据 (带修剪)
        
        Returns:
            bool: 操作是否成功
        """
        print("\n" + "="*80)
        print("🚀 开始数据采集任务 (Feature-Ready Pipeline)")
        print("="*80)
        
        temp_file_path = None
        
        try:
            # 1. 获取数据
            load_value, load_timestamp = self.fetch_caiso_load()
            temperature, weather_timestamp = self.fetch_weather_data()
            
            # 使用模拟数据 (如果获取失败)
            if load_value is None:
                print("\n⚠️  CAISO 数据获取失败，使用模拟数据 (仅演示)")
                # 简单模拟: 假设负载在 20000-40000 之间
                import random
                load_value = 25000.0 + random.random() * 5000
                load_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            
            if temperature is None:
                print("\n⚠️  天气数据获取失败，使用默认温度")
                temperature = 25.0
                weather_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # 2. 构造新数据行
            primary_timestamp = load_timestamp
            hour = primary_timestamp.hour
            day_of_week = primary_timestamp.weekday()
            price = self._get_price_by_hour(hour)
            
            new_row = {
                'Date': primary_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'Hour': hour,
                'DayOfWeek': day_of_week,
                'Temperature': round(temperature, 2),
                'Price': price,
                'Site_Load': round(load_value, 2)
            }
            
            print("\n📊 新数据行:")
            print(f"   Date: {new_row['Date']}")
            print(f"   Load: {new_row['Site_Load']} kW")
            
            # 3. 下载现有数据
            print(f"\n� 从 Storage 下载现有数据: {self.csv_file_path}")
            temp_file_path = self.storage_service.download_to_temp(self.csv_file_path)
            
            if temp_file_path:
                df = pd.read_csv(temp_file_path)
                print(f"   ✓ 现有数据: {len(df)} 行")
            else:
                print("   ℹ️  文件不存在，创建新 DataFrame")
                df = pd.DataFrame()

            # 4. 追加新行 (仅包含原始列)
            # 确保列名一致性，如果 df 为空，直接创建
            new_df = pd.DataFrame([new_row])
            df = pd.concat([df, new_df], ignore_index=True)
            
            # 5. 修剪数据 (保留最近 5000 行，减少计算量)
            # 注意：必须保留足够的历史数据以计算 Lag_168h
            MAX_ROWS = 5000
            if len(df) > MAX_ROWS:
                df = df.iloc[-MAX_ROWS:].reset_index(drop=True)
                print(f"   ✂️  修剪数据至 {len(df)} 行")
            
            # 6. 计算高级特征
            # 这是关键步骤：利用历史数据动态生成 Lag/Rolling 特征
            print("\n⚙️  计算高级特征...")
            processor = EnergyDataProcessor()
            
            # [新增] 添加增强时间特征 (Month, Season, IsHoliday...)
            # 这确保了 cleaned_energy_data_all.csv 包含所有数模所需的特征
            # 确保 Date 列是 datetime 类型
            if df['Date'].dtype == 'object':
                df['Date'] = pd.to_datetime(df['Date'])
            
            df = processor.add_enhanced_time_features(df)
            
            # 这里的巧妙之处：
            # 我们传入 dropna=False，这样前面 168 行会有 NaN (因为没有更早的历史)，
            # 但最新的行 (我们刚追加的) 会有完整的 Lag/Rolling 特征 (因为有之前的 4800+ 行做支撑)。
            # 这样我们就保证了最新数据的完整性。
            df_processed = processor.add_advanced_features(
                df,
                dropna=False,
                use_enhanced=True,
                compute_context='hourly_ingest',
            )
            
            # 检查最后一行是否有 NaN (理论上不应该，除非数据太少)
            last_row = df_processed.iloc[-1]
            if last_row.isnull().any():
                print("   ⚠️  警告: 最新一行包含 NaN (可能是冷启动数据不足)")
                print(last_row[last_row.isnull()])
            else:
                print("   ✓ 最新一行特征计算完整")
            
            # 7. 保存回 Storage
            # 保存时使用临时文件
            import tempfile
            fd, save_path = tempfile.mkstemp(suffix='.csv')
            os.close(fd)
            
            df_processed.to_csv(save_path, index=False)
            
            print(f"\n💾 上传更新后的数据: {len(df_processed)} 行")
            with open(save_path, 'rb') as f:
                self.storage_service.upload_file(
                    f, 
                    self.csv_file_path, 
                    content_type='text/csv'
                )
            
            # 清理
            os.remove(save_path)
            
            print("\n" + "="*80)
            print("✅ 数据采集与特征更新完成!")
            print("="*80 + "\n")
            return True
            
        except Exception as e:
            print(f"\n❌ 任务失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass


# 测试代码
if __name__ == "__main__":
    print("\n🧪 测试 ExternalDataService\n")
    
    service = ExternalDataService()
    success = service.fetch_and_publish()
    
    if success:
        print("\n✅ 测试成功!")
    else:
        print("\n❌ 测试失败!")
