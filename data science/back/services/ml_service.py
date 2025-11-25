"""
机器学习服务模块 - 能源负载预测
ML Service Module for Energy Load Prediction

使用随机森林回归模型预测未来24小时的能源负载
"""

import pandas as pd
import numpy as np
import joblib
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Union
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings

warnings.filterwarnings('ignore')


class EnergyPredictor:
    """
    能源负载预测器
    
    使用随机森林模型预测未来24小时的能源负载
    支持模型训练、保存、加载和推理
    """
    
    def __init__(self, model_path: str = None):
        """
        初始化预测器
        
        Args:
            model_path: 本地兜底模型路径（可选），主要从 Firebase Storage 加载
        """
        # 获取项目根目录
        self.script_dir = Path(__file__).parent  # services 目录
        self.back_dir = self.script_dir.parent  # back 目录
        
        # Firebase Storage 模型路径（主要存储位置）
        self.firebase_model_path = 'models/rf_model.joblib'
        
        # 本地兜底模型路径（部署包中自带的模型，仅用于首次加载）
        if model_path:
            self.local_model_path = Path(model_path)
        else:
            self.local_model_path = self.back_dir / 'models' / 'rf_model.joblib'
        
        # 初始化 StorageService
        from services.storage_service import StorageService
        self.storage_service = StorageService()
        
        # 初始化模型
        self.model: Optional[RandomForestRegressor] = None
        
        # 特征列表
        self.feature_columns = ['Hour', 'DayOfWeek', 'Temperature', 'Price']
        self.target_column = 'Site_Load'
        
        print(f"📁 Firebase Storage 模型路径: {self.firebase_model_path}")
        print(f"📁 本地兜底模型路径: {self.local_model_path}")
    
    def _get_price(self, hour: int) -> float:
        """
        根据小时返回峰谷电价
        
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
    
    def _save_model_metadata(self, metadata: dict) -> bool:
        """
        保存模型元数据到 Firebase Storage (JSON 文件)
        
        Args:
            metadata: 模型元数据字典
            
        Returns:
            是否保存成功
        """
        try:
            import json
            from datetime import datetime
            
            # 添加更新时间戳
            metadata['updated_at'] = datetime.now().isoformat()
            
            # 转换为 JSON 字符串
            json_data = json.dumps(metadata, indent=2, ensure_ascii=False)
            
            # 上传到 Storage (使用临时文件确保 Content-Type 正确)
            import tempfile
            metadata_path = 'models/model_metadata.json'
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                f.write(json_data)
                temp_path = f.name
            
            try:
                with open(temp_path, 'rb') as f:
                    self.storage_service.bucket.blob(metadata_path).upload_from_file(
                        f, 
                        content_type='application/json'
                    )
            finally:
                import os
                os.unlink(temp_path)
            
            print(f"   ✓ 模型元数据已保存到 Firebase Storage: {metadata_path}")
            return True
            
        except Exception as e:
            print(f"   ❌ 保存模型元数据失败: {str(e)}")
            return False
    
    @staticmethod
    def get_model_metadata() -> Optional[dict]:
        """
        从 Firebase Storage 获取模型元数据 (JSON 文件)
        
        Returns:
            模型元数据字典，如果不存在返回 None
        """
        try:
            import json
            from services.storage_service import StorageService
            
            # 创建 Storage 服务实例
            storage = StorageService()
            
            # 下载元数据 JSON
            metadata_path = 'models/model_metadata.json'
            json_bytes = storage.download_file(metadata_path)
            
            # 解析 JSON
            metadata = json.loads(json_bytes.decode('utf-8'))
            return metadata
                
        except Exception as e:
            print(f"获取模型元数据失败: {str(e)}")
            return None
    
    def train_model(
        self, 
        data_path: str = None,
        n_estimators: int = 100,
        test_size: float = 0.2,
        random_state: int = 42,
        use_firebase_storage: bool = True
    ) -> Dict[str, float]:
        """
        训练随机森林模型
        
        Args:
            data_path: 数据文件路径，默认为 data/processed/cleaned_energy_data_all.csv
            n_estimators: 随机森林树的数量
            test_size: 测试集比例
            random_state: 随机种子
            use_firebase_storage: 是否从 Firebase Storage 下载数据 (GAE 环境必须为 True)
            
        Returns:
            包含评估指标的字典 (MAE, RMSE)
        """
        print("\n" + "="*80)
        print("🚀 开始训练能源负载预测模型")
        print("="*80 + "\n")
        
        temp_data_path = None
        
        try:
            # 从 Firebase Storage 下载数据
            if use_firebase_storage:
                print("📥 从 Firebase Storage 下载训练数据...")
                from services.storage_service import StorageService
                
                storage_service = StorageService()
                firebase_path = data_path or 'data/processed/cleaned_energy_data_all.csv'
                
                temp_data_path = storage_service.download_to_temp(firebase_path)
                
                if temp_data_path is None:
                    raise FileNotFoundError(f"无法从 Firebase Storage 下载数据: {firebase_path}")
                
                data_path = temp_data_path
                print(f"   ✓ 数据已下载到: {data_path}")
            else:
                # 本地文件模式 (开发环境)
                if data_path is None:
                    # 尝试多个可能的路径
                    possible_paths = [
                        self.back_dir.parent / 'data' / 'processed' / 'cleaned_energy_data_all.csv',
                        self.back_dir / 'data' / 'processed' / 'cleaned_energy_data_all.csv',
                    ]
                    data_path = None
                    for path in possible_paths:
                        if path.exists():
                            data_path = path
                            break
                    if data_path is None:
                        data_path = possible_paths[0]  # 使用第一个作为默认
                else:
                    data_path = Path(data_path)
            
            # 读取数据
            print(f"📖 读取数据: {data_path}")
            try:
                df = pd.read_csv(data_path, parse_dates=['Date'])
                print(f"   ✓ 数据读取成功: {len(df)} 行 × {len(df.columns)} 列")
            except FileNotFoundError:
                raise FileNotFoundError(f"数据文件不存在: {data_path}")
            except Exception as e:
                raise Exception(f"读取数据时出错: {str(e)}")
            
            # 检查必需列
            required_cols = self.feature_columns + [self.target_column]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"数据缺少必需列: {missing_cols}")
            
            # 处理缺失值
            print(f"\n🔍 检查数据质量...")
            null_counts = df[required_cols].isnull().sum()
            if null_counts.sum() > 0:
                print(f"   ⚠️  发现缺失值:")
                for col, count in null_counts[null_counts > 0].items():
                    print(f"      - {col}: {count} 个")
                
                # 对于 Temperature，使用均值填充
                if 'Temperature' in null_counts and null_counts['Temperature'] > 0:
                    mean_temp = df['Temperature'].mean()
                    df['Temperature'].fillna(mean_temp, inplace=True)
                    print(f"   ✓ Temperature 缺失值已用均值填充: {mean_temp:.2f}°C")
            else:
                print(f"   ✓ 无缺失值")
            
            # 准备特征和目标变量
            print(f"\n📊 准备训练数据...")
            X = df[self.feature_columns].copy()
            y = df[self.target_column].copy()
            
            print(f"   - 特征列: {self.feature_columns}")
            print(f"   - 目标变量: {self.target_column}")
            print(f"   - 数据形状: X={X.shape}, y={y.shape}")
            
            # 划分训练集和测试集
            print(f"\n✂️  划分数据集 (训练集: {int((1-test_size)*100)}%, 测试集: {int(test_size*100)}%)...")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=random_state
            )
            
            print(f"   - 训练集: {X_train.shape[0]} 样本")
            print(f"   - 测试集: {X_test.shape[0]} 样本")
            
            # 训练模型
            print(f"\n🌲 训练随机森林模型 (n_estimators={n_estimators})...")
            self.model = RandomForestRegressor(
                n_estimators=n_estimators,
                random_state=random_state,
                n_jobs=-1,  # 使用所有CPU核心
                verbose=0
            )
            
            self.model.fit(X_train, y_train)
            print(f"   ✓ 模型训练完成!")
            
            # 评估模型
            print(f"\n📈 评估模型性能...")
            
            # 训练集预测
            y_train_pred = self.model.predict(X_train)
            train_mae = mean_absolute_error(y_train, y_train_pred)
            train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
            
            # 测试集预测
            y_test_pred = self.model.predict(X_test)
            test_mae = mean_absolute_error(y_test, y_test_pred)
            test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
            
            print(f"\n   训练集性能:")
            print(f"      - MAE:  {train_mae:.2f} kW")
            print(f"      - RMSE: {train_rmse:.2f} kW")
            
            print(f"\n   测试集性能:")
            print(f"      - MAE:  {test_mae:.2f} kW")
            print(f"      - RMSE: {test_rmse:.2f} kW")
            
            # 特征重要性
            print(f"\n🔍 特征重要性:")
            feature_importance = pd.DataFrame({
                'Feature': self.feature_columns,
                'Importance': self.model.feature_importances_
            }).sort_values('Importance', ascending=False)
            
            for _, row in feature_importance.iterrows():
                print(f"      - {row['Feature']}: {row['Importance']:.4f}")
            
            # 保存模型到 Firebase Storage
            print(f"\n💾 保存模型到 Firebase Storage: {self.firebase_model_path}")
            temp_model_path = None
            try:
                # Step A: 创建临时文件
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.joblib', delete=False) as tmp_file:
                    temp_model_path = tmp_file.name
                    print(f"   - 临时文件: {temp_model_path}")
                
                # Step B: 保存模型到临时文件
                joblib.dump(self.model, temp_model_path)
                print(f"   ✓ 模型已保存到临时文件")
                
                # Step C: 上传到 Firebase Storage
                with open(temp_model_path, 'rb') as f:
                    self.storage_service.upload_file(
                        file_data=f,
                        destination_path=self.firebase_model_path,
                        content_type='application/octet-stream'
                    )
                print(f"   ✓ 模型已上传到 Firebase Storage")
                
            except Exception as e:
                print(f"   ❌ 模型保存失败: {str(e)}")
                raise
            finally:
                # Step D: 清理临时文件
                if temp_model_path and os.path.exists(temp_model_path):
                    try:
                        os.remove(temp_model_path)
                        print(f"   🧹 已清理临时模型文件")
                    except Exception as e:
                        print(f"   ⚠️  清理临时模型文件失败: {str(e)}")
            
            print("\n" + "="*80)
            print("✅ 模型训练完成!")
            print("="*80 + "\n")
            
            # 保存模型元数据到 Firestore (全局元数据)
            try:
                self._save_model_metadata({
                    'model_type': 'Random Forest Regressor',
                    'model_version': datetime.now().strftime('%Y%m%d_%H%M%S'),
                    'trained_at': datetime.now().isoformat(),
                    'metrics': {
                        'train_mae': float(train_mae),
                        'train_rmse': float(train_rmse),
                        'test_mae': float(test_mae),
                        'test_rmse': float(test_rmse)
                    },
                    'training_samples': len(df),
                    'data_source': 'CAISO Real-Time Stream',
                    'feature_importance': feature_importance.to_dict('records'),
                    'model_path': self.firebase_model_path,
                    'status': 'active'
                })
            except Exception as e:
                print(f"   ⚠️  保存模型元数据失败: {str(e)}")
            
            # 返回评估指标
            return {
                'train_mae': train_mae,
                'train_rmse': train_rmse,
                'test_mae': test_mae,
                'test_rmse': test_rmse,
                'feature_importance': feature_importance.to_dict('records')
            }
        
        finally:
            # 清理临时文件
            if temp_data_path and os.path.exists(temp_data_path):
                try:
                    os.remove(temp_data_path)
                    print(f"🧹 清理临时训练数据文件")
                except Exception as e:
                    print(f"⚠️  清理临时文件失败: {str(e)}")
    
    def load_model(self) -> bool:
        """
        加载已保存的模型（优先从 Firebase Storage）
        
        Returns:
            是否加载成功
            
        Raises:
            FileNotFoundError: 模型文件不存在
            Exception: 加载模型时出错
        """
        print(f"📂 加载模型...")
        temp_model_path = None
        
        try:
            # Step A: 检查 Firebase Storage 中是否存在模型
            print(f"   - 检查 Firebase Storage: {self.firebase_model_path}")
            
            if self.storage_service.file_exists(self.firebase_model_path):
                print(f"   ✓ Firebase Storage 中存在模型")
                
                # Step B: 下载到临时目录
                temp_model_path = self.storage_service.download_to_temp(self.firebase_model_path)
                
                if temp_model_path is None:
                    raise Exception("从 Firebase Storage 下载模型失败")
                
                print(f"   ✓ 模型已下载到: {temp_model_path}")
                
                # Step C: 从临时文件加载模型
                self.model = joblib.load(temp_model_path)
                print(f"   ✓ 模型加载成功 (来源: Firebase Storage)")
                return True
            
            else:
                # Step D: Firebase 中没有模型，尝试加载本地兜底模型
                print(f"   ⚠️  Firebase Storage 中无模型，尝试加载本地兜底模型")
                
                if not self.local_model_path.exists():
                    raise FileNotFoundError(
                        f"模型文件不存在:\n"
                        f"  - Firebase Storage: {self.firebase_model_path} (不存在)\n"
                        f"  - 本地路径: {self.local_model_path} (不存在)\n"
                        f"请先调用 train_model() 训练模型。"
                    )
                
                self.model = joblib.load(self.local_model_path)
                print(f"   ✓ 模型加载成功 (来源: 本地兜底文件)")
                return True
        
        except Exception as e:
            raise Exception(f"加载模型时出错: {str(e)}")
        
        finally:
            # 清理临时文件
            if temp_model_path and os.path.exists(temp_model_path):
                try:
                    os.remove(temp_model_path)
                    print(f"   🧹 已清理临时模型文件")
                except Exception as e:
                    print(f"   ⚠️  清理临时模型文件失败: {str(e)}")
    
    def predict_next_24h(
        self,
        start_time: Union[str, datetime],
        temp_forecast_list: Optional[List[float]] = None
    ) -> List[Dict[str, Union[datetime, float]]]:
        """
        预测未来24小时的能源负载
        
        Args:
            start_time: 开始时间（字符串格式 'YYYY-MM-DD HH:00:00' 或 datetime 对象）
            temp_forecast_list: 未来24小时的温度预测列表，如果为None则使用默认值25.0°C
            
        Returns:
            包含预测结果的字典列表，每个字典包含:
                - datetime: 时间戳
                - predicted_load: 预测负载 (kW)
                - temperature: 温度 (°C)
                - price: 电价 (元/kWh)
                - hour: 小时 (0-23)
                - day_of_week: 星期几 (0-6)
                
        Raises:
            ValueError: 模型未加载或参数错误
        """
        # 检查模型是否已加载
        if self.model is None:
            raise ValueError(
                "模型未加载，请先调用 load_model() 或 train_model()"
            )
        
        # 转换开始时间
        if isinstance(start_time, str):
            start_time = pd.to_datetime(start_time)
        
        print(f"\n🔮 预测未来24小时负载 (从 {start_time} 开始)...")
        
        # 处理温度预测
        if temp_forecast_list is None:
            print(f"   ⚠️  未提供温度预测，使用默认值 25.0°C")
            temp_forecast_list = [25.0] * 24
        elif len(temp_forecast_list) != 24:
            raise ValueError(
                f"温度预测列表长度必须为24，当前为 {len(temp_forecast_list)}"
            )
        
        # 生成未来24小时的时间点
        time_points = [start_time + timedelta(hours=i) for i in range(24)]
        
        # 构建预测数据
        prediction_data = []
        for i, dt in enumerate(time_points):
            hour = dt.hour
            day_of_week = dt.weekday()
            temperature = temp_forecast_list[i]
            price = self._get_price(hour)
            
            prediction_data.append({
                'Hour': hour,
                'DayOfWeek': day_of_week,
                'Temperature': temperature,
                'Price': price
            })
        
        # 创建DataFrame
        X_pred = pd.DataFrame(prediction_data)
        
        # 进行预测
        try:
            predictions = self.model.predict(X_pred)
            print(f"   ✓ 预测完成!")
        except Exception as e:
            raise Exception(f"预测时出错: {str(e)}")
        
        # 构建结果
        results = []
        for i, (dt, pred_load) in enumerate(zip(time_points, predictions)):
            results.append({
                'datetime': dt,
                'predicted_load': float(pred_load),
                'temperature': temp_forecast_list[i],
                'price': prediction_data[i]['Price'],
                'hour': prediction_data[i]['Hour'],
                'day_of_week': prediction_data[i]['DayOfWeek']
            })
        
        # 打印统计信息
        avg_load = np.mean(predictions)
        max_load = np.max(predictions)
        min_load = np.min(predictions)
        
        print(f"\n   📊 预测统计:")
        print(f"      - 平均负载: {avg_load:.2f} kW")
        print(f"      - 最大负载: {max_load:.2f} kW (时刻: {time_points[np.argmax(predictions)].strftime('%H:%M')})")
        print(f"      - 最小负载: {min_load:.2f} kW (时刻: {time_points[np.argmin(predictions)].strftime('%H:%M')})")
        
        return results
    
    def predict_single(
        self,
        hour: int,
        day_of_week: int,
        temperature: float,
        price: float = None
    ) -> float:
        """
        单点预测
        
        Args:
            hour: 小时 (0-23)
            day_of_week: 星期几 (0-6)
            temperature: 温度 (°C)
            price: 电价，如果为None则自动根据hour计算
            
        Returns:
            预测负载 (kW)
        """
        if self.model is None:
            raise ValueError("模型未加载，请先调用 load_model() 或 train_model()")
        
        if price is None:
            price = self._get_price(hour)
        
        X = pd.DataFrame([{
            'Hour': hour,
            'DayOfWeek': day_of_week,
            'Temperature': temperature,
            'Price': price
        }])
        
        prediction = self.model.predict(X)[0]
        return float(prediction)


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
    metrics = predictor.train_model(n_estimators=100)
    
    # 3. 测试加载模型
    print("\n【步骤 3】测试加载模型")
    print("-" * 80)
    predictor_new = EnergyPredictor()
    predictor_new.load_model()
    
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
    
    for hour, dow, temp, desc in test_cases:
        pred = predictor_new.predict_single(hour, dow, temp)
        print(f"   {desc}: {pred:.2f} kW")
    
    # 7. 总结
    print("\n" + "="*80)
    print("✅ 测试完成!")
    print("="*80)
    print(f"\n模型性能:")
    print(f"   - 测试集 MAE:  {metrics['test_mae']:.2f} kW")
    print(f"   - 测试集 RMSE: {metrics['test_rmse']:.2f} kW")
    print(f"\n模型已保存到: {predictor.model_path}")
    print(f"可以通过 load_model() 加载使用\n")


if __name__ == "__main__":
    main()
