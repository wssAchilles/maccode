"""
能源优化 API 路由
处理电池储能系统优化调度请求

集成机器学习预测和 Gurobi 优化
"""

from flask import Blueprint, jsonify, request
from config import Config
from services.firebase_service import require_auth
from utils.exceptions import ValidationError
from middleware.rate_limit import rate_limit
import logging
from datetime import datetime, timedelta
import sys
from pathlib import Path
import importlib.util

logger = logging.getLogger(__name__)

# 确保 back 目录在 sys.path 中 (GAE 运行在 /workspace，下级为 /workspace/back)
BACK_DIR = Path(__file__).resolve().parent.parent
if str(BACK_DIR) not in sys.path:
    sys.path.insert(0, str(BACK_DIR))


def _load_service_class(module_name: str, class_name: str):
    """加载服务类，兼容本地与 GAE 路径。"""
    try:
        module = __import__(f"services.{module_name}", fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError) as err:
        logger.warning(f"标准导入 services.{module_name} 失败: {err}")
        module_path = BACK_DIR / 'services' / f"{module_name}.py"
        if not module_path.exists():
            logger.error(f"服务文件不存在: {module_path}")
            return None
        spec = importlib.util.spec_from_file_location(f"services.{module_name}", module_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, class_name, None)
        logger.error(f"无法加载服务模块: {module_name}")
        return None


EnergyPredictor = _load_service_class('ml_service', 'EnergyPredictor')
EnergyOptimizer = _load_service_class('optimization_service', 'EnergyOptimizer')


def _generate_importance_interpretation(importance: dict) -> str:
    """
    生成特征重要性的人类可读解释
    
    Args:
        importance: 特征名到重要性分数的映射字典
        
    Returns:
        解释文字
    """
    if not importance:
        return "特征重要性数据不可用"
    
    # 特征中文名称映射
    feature_names = {
        'Hour': '小时',
        'DayOfWeek': '星期',
        'Temperature': '温度',
        'Price': '电价'
    }
    
    sorted_items = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    top_feature, top_score = sorted_items[0]
    top_name = feature_names.get(top_feature, top_feature)
    
    return f"{top_name}是影响负载预测的最重要因素 ({top_score*100:.1f}%)，" \
           f"表明每日用电量与{top_name}变化高度相关"


optimization_bp = Blueprint('optimization', __name__, url_prefix='/api/optimization')


# 电池配置（可以从配置文件或数据库读取）
# 注意：负载规模约 20000-30000 kW，需要工业级储能
BATTERY_CONFIG = {
    'capacity': 100.0,      # kWh (适配当前 100-400kW 负载规模)
    'max_power': 40.0,      # kW (充放电功率)
    'efficiency': 0.95      # 95% (高效能电池)
}


@optimization_bp.route('/run', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=20, window_seconds=60)
@require_auth
def run_optimization():
    """
    执行能源优化调度
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          {
            "initial_soc": 0.5,           // 初始电量 (0.0-1.0)
            "target_date": "2024-11-24",  // 可选，默认明天
            "temperature_forecast": [24.0, 23.5, ...],  // 可选，24个值
            "battery_capacity": 13.5,     // 可选，覆盖默认配置
            "battery_power": 5.0,         // 可选
            "battery_efficiency": 0.95    // 可选
          }
    
    响应:
        {
            "success": true,
            "optimization": {
                "status": "Optimal",
                "chart_data": [
                    {
                        "hour": 0,
                        "datetime": "2024-11-24T00:00:00",
                        "load": 120.42,
                        "price": 0.3,
                        "battery_action": 0.0,
                        "charge_power": 0.0,
                        "discharge_power": 0.0,
                        "soc": 50.0,
                        "grid_power": 120.42
                    },
                    ...
                ],
                "summary": {
                    "total_cost_without_battery": 2602.57,
                    "total_cost_with_battery": 2591.88,
                    "savings": 10.69,
                    "savings_percent": 0.4,
                    "total_load": 4761.99,
                    "total_charged": 7.11,
                    "total_discharged": 12.83,
                    "peak_load": 380.32,
                    "min_load": 113.05
                },
                "strategy": {
                    "charging_hours": [3, 5],
                    "discharging_hours": [18, 19, 20],
                    "charging_count": 2,
                    "discharging_count": 3
                }
            },
            "prediction": {
                "target_date": "2024-11-24",
                "avg_load": 198.42,
                "peak_load": 380.32,
                "min_load": 113.05
            },
            "battery_config": {
                "capacity": 13.5,
                "max_power": 5.0,
                "efficiency": 0.95
            }
        }
    """
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    # 检查服务是否已加载
    if EnergyPredictor is None or EnergyOptimizer is None:
        logger.error("优化服务未能正确加载")
        return jsonify({
            'success': False,
            'error': 'SERVICE_UNAVAILABLE',
            'message': '优化服务暂时不可用，请稍后重试'
        }), 503
    
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        logger.info(f"[{uid}] 收到优化请求")
        
        # ====================================================================
        # 步骤 1: 参数验证
        # ====================================================================
        initial_soc = data.get('initial_soc', 0.5)
        target_date = data.get('target_date')
        temp_forecast = data.get('temperature_forecast')
        temp_adjust = float(data.get('temperature_adjust', 0.0))
        
        # 验证 initial_soc
        if not isinstance(initial_soc, (int, float)) or not 0 <= initial_soc <= 1:
            raise ValidationError('initial_soc 必须在 0.0 到 1.0 之间')
        
        # 解析目标日期
        if target_date:
            try:
                target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
                target_datetime = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                raise ValidationError('target_date 格式错误，应为 YYYY-MM-DD')
        else:
            # 默认明天
            target_datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            target_date = target_datetime.strftime('%Y-%m-%d')
        
        # 验证温度预测
        if temp_forecast is not None:
            if not isinstance(temp_forecast, list) or len(temp_forecast) != 24:
                raise ValidationError('temperature_forecast 必须是包含 24 个值的列表')
        
        # 电池配置（允许覆盖）
        battery_capacity = data.get('battery_capacity', BATTERY_CONFIG['capacity'])
        battery_power = data.get('battery_power', BATTERY_CONFIG['max_power'])
        battery_efficiency = data.get('battery_efficiency', BATTERY_CONFIG['efficiency'])
        
        logger.info(f"[{uid}] 优化参数: date={target_date}, soc={initial_soc}, "
                   f"battery={battery_capacity}kWh/{battery_power}kW")
        
        # ====================================================================
        # 步骤 2: 负载预测
        # ====================================================================
        logger.info(f"[{uid}] 开始负载预测...")
        
        # 获取模型元数据
        model_metadata = EnergyPredictor.get_model_metadata()
        
        try:
            predictor = EnergyPredictor()
            predictor.load_model()
            
            predictions = predictor.predict_next_24h(
                start_time=target_datetime,
                temp_forecast_list=temp_forecast,
                temp_adjust_delta=temp_adjust
            )
            
            logger.info(f"[{uid}] 负载预测完成: {len(predictions)} 小时")
            
        except FileNotFoundError as e:
            logger.error(f"[{uid}] 模型文件未找到: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'MODEL_NOT_FOUND',
                'message': '预测模型未找到，请先训练模型'
            }), 404
        
        except Exception as e:
            logger.error(f"[{uid}] 预测失败: {str(e)}", exc_info=True)
            return jsonify({
                'success': False,
                'error': 'PREDICTION_ERROR',
                'message': f'负载预测失败: {str(e)}'
            }), 500
        
        # 提取负载和电价
        load_profile = [p['predicted_load'] for p in predictions]
        price_profile = [p['price'] for p in predictions]
        
        avg_load = sum(load_profile) / len(load_profile)
        peak_load = max(load_profile)
        min_load = min(load_profile)
        
        logger.info(f"[{uid}] 负载统计: avg={avg_load:.2f}, peak={peak_load:.2f}, min={min_load:.2f}")
        
        # ====================================================================
        # 步骤 3: 优化调度
        # ====================================================================
        logger.info(f"[{uid}] 开始优化调度...")
        
        try:
            optimizer = EnergyOptimizer(
                battery_capacity=battery_capacity,
                max_power=battery_power,
                efficiency=battery_efficiency
            )
            
            result = optimizer.optimize_schedule(
                load_profile=load_profile,
                price_profile=price_profile,
                initial_soc=initial_soc
            )
            
            logger.info(f"[{uid}] 优化完成: status={result['status']}")
            
        except Exception as e:
            error_msg = str(e)
            
            # 检查是否是许可证错误
            if 'license' in error_msg.lower() or 'gurobi' in error_msg.lower():
                logger.error(f"[{uid}] Gurobi 许可证错误: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': 'LICENSE_ERROR',
                    'message': 'Optimization failed: Gurobi license not found'
                }), 500
            else:
                logger.error(f"[{uid}] 优化失败: {error_msg}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': 'OPTIMIZATION_ERROR',
                    'message': f'优化失败: {error_msg}'
                }), 500
        
        # ====================================================================
        # 步骤 4: 检查优化状态
        # ====================================================================
        if result['status'] != 'Optimal':
            logger.warning(f"[{uid}] 优化未成功: {result['status']}")
            return jsonify({
                'success': False,
                'error': 'OPTIMIZATION_FAILED',
                'message': result.get('error', '优化求解失败'),
                'status': result['status']
            }), 400
        
        # ====================================================================
        # 步骤 5: 格式化结果（前端友好）
        # ====================================================================
        logger.info(f"[{uid}] 格式化优化结果...")
        
        schedule = result['schedule']
        
        # 构建图表数据
        chart_data = []
        for item in schedule:
            dt = target_datetime + timedelta(hours=item['hour'])
            
            chart_data.append({
                'hour': item['hour'],
                'datetime': dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'load': round(item['load'], 2),
                'price': item['price'],
                'battery_action': round(item['battery_action'], 2),
                'charge_power': round(item['charge_power'], 2),
                'discharge_power': round(item['discharge_power'], 2),
                'soc': round(item['soc'] * 100, 1),  # 转换为百分比
                'stored_energy': round(item['stored_energy'], 2),
                'grid_power': round(item['load'] + item['battery_action'], 2)  # 从电网购买的功率
            })
        
        # 计算总充放电量
        total_charged = sum(item['charge_power'] for item in schedule)
        total_discharged = sum(item['discharge_power'] for item in schedule)
        total_load = sum(item['load'] for item in schedule)
        
        # 提取充放电时段
        charging_hours = [item['hour'] for item in schedule if item['battery_action'] > 0.01]
        discharging_hours = [item['hour'] for item in schedule if item['battery_action'] < -0.01]
        
        # 构建总结数据
        summary = {
            'total_cost_without_battery': round(result['total_cost_without_battery'], 2),
            'total_cost_with_battery': round(result['total_cost_with_battery'], 2),
            'savings': round(result['savings'], 2),
            'savings_percent': round(result['savings_percent'], 2),
            'total_load': round(total_load, 2),
            'total_charged': round(total_charged, 2),
            'total_discharged': round(total_discharged, 2),
            'peak_load': round(peak_load, 2),
            'min_load': round(min_load, 2),
            'avg_load': round(avg_load, 2)
        }
        
        # 构建策略数据
        strategy = {
            'charging_hours': charging_hours,
            'discharging_hours': discharging_hours,
            'charging_count': len(charging_hours),
            'discharging_count': len(discharging_hours)
        }
        
        # ====================================================================
        # 步骤 6: 构建响应
        # ====================================================================
        response = {
            'success': True,
            'optimization': {
                'status': result['status'],
                'chart_data': chart_data,
                'summary': summary,
                'strategy': strategy,
                'diagnostics': result.get('diagnostics'),
                'constraint_hits': result.get('constraint_hits')
            },
            'prediction': {
                'target_date': target_date,
                'avg_load': round(avg_load, 2),
                'peak_load': round(peak_load, 2),
                'min_load': round(min_load, 2)
            },
            'battery_config': {
                'capacity': battery_capacity,
                'max_power': battery_power,
                'efficiency': battery_efficiency,
                'initial_soc': initial_soc
            }
        }
        
        # 安全获取模型可解释性数据（避免 SHAP 错误影响整个响应）
        try:
            feature_importance = predictor.get_feature_importance()
            response['model_explainability'] = {
                'feature_importance': feature_importance,
                'feature_descriptions': {
                    'Hour': '小时 (0-23)',
                    'DayOfWeek': '星期几 (0=周一, 6=周日)',
                    'Temperature': '温度 (°C)',
                    'Price': '电价 (元/kWh)'
                },
                'interpretation': _generate_importance_interpretation(feature_importance)
            }
            logger.info(f"[{uid}] model_explainability 获取成功")
        except Exception as e:
            logger.warning(f"[{uid}] 获取 model_explainability 失败: {str(e)}")
            # 不添加 model_explainability 字段，前端会处理 null
        
        
        # 添加模型信息和实时监控指标
        model_info = model_metadata if model_metadata else {
            'model_type': 'Random Forest Regressor',
            'status': 'unknown',
            'data_source': 'CAISO Real-Time Stream'
        }
        
        # 确保 metrics 字段存在（从训练元数据中获取）
        if 'metrics' not in model_info:
            model_info['metrics'] = {}
        
        # 获取在线模型性能评估 (MLOps)
        # 注意：在线评估的 metrics 会与训练时的 metrics 合并，而不是覆盖
        try:
            online_metrics = predictor.evaluate_recent_performance(hours=24)
            if online_metrics.get('status') == 'success':
                # 合并：保留训练时的 r2_score 和 mape（如果在线评估没有更新它们）
                # 【修改】不要覆盖 r2_score 和 mape，保持显示模型在测试集上的稳定性能
                # 在线指标仅保留 last_data_point 和 sample_count 等辅助信息
                protected_metrics = ['r2_score', 'mape', 'test_mae', 'test_rmse']
                
                for key, value in online_metrics.items():
                    if key != 'status' and key not in protected_metrics:
                        model_info['metrics'][key] = value
                        
                # 也可以选择将在线指标另存为 online_metrics 字段供前端展示（如果有对应UI）
                response['online_metrics'] = online_metrics
                
                logger.info(f"[{uid}] 在线评估成功，辅助指标已合并")
        except Exception as e:
            logger.warning(f"获取在线模型性能指标失败: {e}，使用训练时保存的指标")
            
        response['model_info'] = model_info
        
        logger.info(f"[{uid}] 优化请求完成: 节省 {summary['savings']:.2f} 元 "
                   f"({summary['savings_percent']:.1f}%)")
        
        return jsonify(response), 200
    
    except ValidationError as e:
        logger.warning(f"参数校验失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'VALIDATION_ERROR',
            'message': str(e)
        }), 400
    
    except Exception as e:
        logger.error(f"优化请求异常: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500


@optimization_bp.route('/config', methods=['GET', 'OPTIONS'])
@rate_limit(max_requests=30, window_seconds=60)
def get_config():
    """
    获取当前电池配置
    
    请求:
        - Method: GET
        - 无需认证
    
    响应:
        {
            "success": true,
            "config": {
                "battery_capacity": 13.5,
                "max_power": 5.0,
                "efficiency": 0.95,
                "description": "Tesla Powerwall"
            },
            "price_schedule": {
                "valley": 0.3,
                "normal": 0.6,
                "peak": 1.0,
                "valley_hours": "00:00-08:00, 22:00-24:00",
                "normal_hours": "08:00-18:00",
                "peak_hours": "18:00-22:00"
            }
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        logger.info("获取优化配置")
        
        response = {
            'success': True,
            'config': {
                'battery_capacity': BATTERY_CONFIG['capacity'],
                'max_power': BATTERY_CONFIG['max_power'],
                'efficiency': BATTERY_CONFIG['efficiency'],
                'description': 'Tesla Powerwall',
                'unit_capacity': 'kWh',
                'unit_power': 'kW'
            },
            'price_schedule': {
                'valley': Config.PRICE_SCHEDULE['valley'],
                'normal': Config.PRICE_SCHEDULE['normal'],
                'peak': Config.PRICE_SCHEDULE['peak'],
                'valley_hours': Config.PRICE_SCHEDULE['valley_desc'],
                'normal_hours': Config.PRICE_SCHEDULE['normal_desc'],
                'peak_hours': Config.PRICE_SCHEDULE['peak_desc'],
                'currency': Config.PRICE_SCHEDULE['currency']
            }
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        logger.error(f"获取配置失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500


@optimization_bp.route('/model-info', methods=['GET', 'OPTIONS'])
@rate_limit(max_requests=30, window_seconds=60)
def get_model_info():
    """
    获取ML模型元数据和健康状态
    
    请求:
        - Method: GET
        - 无需认证
    
    响应:
        {
            "success": true,
            "model_info": {
                "model_type": "Random Forest Regressor",
                "model_version": "20241125_120000",
                "trained_at": "2024-11-25T12:00:00",
                "metrics": {
                    "test_mae": 125.4,
                    "test_rmse": 180.2
                },
                "training_samples": 8760,
                "data_source": "CAISO Real-Time Stream",
                "status": "active"
            }
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        logger.info("获取ML模型信息")
        
        # 检查服务是否已加载
        if EnergyPredictor is None:
            return jsonify({
                'success': False,
                'error': 'SERVICE_UNAVAILABLE',
                'message': 'ML服务暂时不可用'
            }), 503
        
        # 获取模型元数据
        model_metadata = EnergyPredictor.get_model_metadata()
        
        if model_metadata:
            # 格式化时间戳
            if 'updated_at' in model_metadata and hasattr(model_metadata['updated_at'], 'isoformat'):
                model_metadata['updated_at'] = model_metadata['updated_at'].isoformat()
            
            return jsonify({
                'success': True,
                'model_info': model_metadata
            }), 200
        else:
            # 模型元数据不存在，返回默认信息
            return jsonify({
                'success': True,
                'model_info': {
                    'model_type': 'Random Forest Regressor',
                    'status': 'not_trained',
                    'data_source': 'CAISO Real-Time Stream',
                    'message': '模型尚未训练或元数据不可用'
                }
            }), 200
    
    except Exception as e:
        logger.error(f"获取模型信息失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500


@optimization_bp.route('/simulate', methods=['POST', 'OPTIONS'])
@rate_limit(max_requests=20, window_seconds=60)
@require_auth
def simulate_scenario():
    """
    场景模拟：对比不同电池配置的效果
    
    请求:
        - Method: POST
        - Headers: Authorization: Bearer <Firebase ID Token>
        - Body: JSON
          {
            "target_date": "2024-11-24",
            "scenarios": [
                {"name": "无电池", "capacity": 0, "power": 0},
                {"name": "小型", "capacity": 10, "power": 3},
                {"name": "Powerwall", "capacity": 13.5, "power": 5},
                {"name": "大型", "capacity": 20, "power": 7}
            ]
          }
    
    响应:
        {
            "success": true,
            "comparison": [
                {
                    "scenario": "无电池",
                    "cost": 2602.57,
                    "savings": 0,
                    "savings_percent": 0
                },
                ...
            ],
            "best_scenario": {
                "name": "Powerwall",
                "savings": 10.69
            }
        }
    """
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    
    try:
        user = request.user
        uid = user.get('uid')
        data = request.get_json() or {}
        
        logger.info(f"[{uid}] 收到场景模拟请求")
        
        target_date = data.get('target_date')
        scenarios = data.get('scenarios', [
            {"name": "无电池", "capacity": 0, "power": 0},
            {"name": "小型储能 (50kWh)", "capacity": 50, "power": 20},
            {"name": "中型储能 (100kWh)", "capacity": 100, "power": 40},
            {"name": "大型储能 (200kWh)", "capacity": 200, "power": 80}
        ])
        
        # 解析目标日期
        if target_date:
            target_datetime = datetime.strptime(target_date, '%Y-%m-%d')
            target_datetime = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            target_datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # 预测负载
        predictor = EnergyPredictor()
        predictor.load_model()
        predictions = predictor.predict_next_24h(start_time=target_datetime)
        
        load_profile = [p['predicted_load'] for p in predictions]
        price_profile = [p['price'] for p in predictions]
        
        # 无电池成本
        baseline_cost = sum(l * p for l, p in zip(load_profile, price_profile))
        
        # 对比场景
        comparison = []
        
        for scenario in scenarios:
            name = scenario.get('name', 'Unknown')
            capacity = scenario.get('capacity', 0)
            power = scenario.get('power', 0)
            
            if capacity == 0 or power == 0:
                # 无电池场景
                comparison.append({
                    'scenario': name,
                    'cost': round(baseline_cost, 2),
                    'savings': 0,
                    'savings_percent': 0
                })
            else:
                # 有电池场景
                optimizer = EnergyOptimizer(
                    battery_capacity=capacity,
                    max_power=power,
                    efficiency=0.95
                )
                
                result = optimizer.optimize_schedule(
                    load_profile=load_profile,
                    price_profile=price_profile,
                    initial_soc=0.5
                )
                
                if result['status'] == 'Optimal':
                    comparison.append({
                        'scenario': name,
                        'cost': round(result['total_cost_with_battery'], 2),
                        'savings': round(result['savings'], 2),
                        'savings_percent': round(result['savings_percent'], 2)
                    })
        
        # 找出最佳场景
        best = max(comparison, key=lambda x: x['savings'])
        
        logger.info(f"[{uid}] 场景模拟完成: {len(comparison)} 个场景")
        
        return jsonify({
            'success': True,
            'comparison': comparison,
            'best_scenario': {
                'name': best['scenario'],
                'savings': best['savings'],
                'savings_percent': best['savings_percent']
            },
            'baseline_cost': round(baseline_cost, 2)
        }), 200
    
    except Exception as e:
        logger.error(f"场景模拟失败: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'SERVER_ERROR',
            'message': f'服务器错误: {str(e)}'
        }), 500
