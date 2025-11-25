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
        
        # OpenWeather API 配置
        self.weather_api_key = os.getenv('OPENWEATHER_API_KEY')
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
            
            print(f"   ✓ CAISO 负载: {load_value:.2f} MW")
            print(f"   ✓ 时间戳: {timestamp} (UTC)")
            
            return load_value, timestamp
            
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
        3. 数据对齐和时区统一
        4. 构造数据行
        5. 追加到 CSV 文件 (带滑动窗口)
        
        Returns:
            bool: 操作是否成功
        """
        print("\n" + "="*80)
        print("🚀 开始数据采集任务")
        print("="*80)
        
        try:
            # 1. 获取 CAISO 数据
            load_value, load_timestamp = self.fetch_caiso_load()
            
            # 2. 获取天气数据
            temperature, weather_timestamp = self.fetch_weather_data()
            
            # 3. 数据验证
            if load_value is None:
                print("\n⚠️  CAISO 数据获取失败，使用模拟数据")
                load_value = 25000.0  # 模拟值 (MW)
                load_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            
            if temperature is None:
                print("\n⚠️  天气数据获取失败，使用默认温度")
                temperature = 25.0  # 默认温度 (°C)
                weather_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # 4. 时间对齐 (使用 CAISO 时间戳作为主时间)
            primary_timestamp = load_timestamp
            
            # 5. 构造数据行
            hour = primary_timestamp.hour
            day_of_week = primary_timestamp.weekday()
            price = self._get_price_by_hour(hour)
            
            new_data = {
                'Date': primary_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'Hour': hour,
                'DayOfWeek': day_of_week,
                'Temperature': round(temperature, 2),
                'Price': price,
                'Site_Load': round(load_value, 2)
            }
            
            print("\n📊 构造的数据行:")
            for key, value in new_data.items():
                print(f"   {key}: {value}")
            
            # 6. 追加到 CSV (带滑动窗口)
            print(f"\n💾 持久化数据到: {self.csv_file_path}")
            success = self.storage_service.append_and_trim_csv(
                file_path=self.csv_file_path,
                new_row_dict=new_data,
                max_rows=5000
            )
            
            if success:
                print("\n" + "="*80)
                print("✅ 数据采集任务完成!")
                print("="*80 + "\n")
                return True
            else:
                print("\n" + "="*80)
                print("❌ 数据采集任务失败!")
                print("="*80 + "\n")
                return False
            
        except Exception as e:
            print(f"\n❌ 数据采集任务异常: {str(e)}")
            import traceback
            traceback.print_exc()
            print("\n" + "="*80)
            print("❌ 数据采集任务失败!")
            print("="*80 + "\n")
            return False


# 测试代码
if __name__ == "__main__":
    print("\n🧪 测试 ExternalDataService\n")
    
    service = ExternalDataService()
    success = service.fetch_and_publish()
    
    if success:
        print("\n✅ 测试成功!")
    else:
        print("\n❌ 测试失败!")
