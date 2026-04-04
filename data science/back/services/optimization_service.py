"""
能源优化服务模块 - 电池储能系统优化调度
Energy Optimization Service - Battery Energy Storage System Scheduling

使用 Gurobi 求解器进行混合整数规划 (MIP) 优化
"""

import os
from time import perf_counter
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
import warnings

from services.secrets import get_secret
from services.compute_acceleration_service import ComputeAccelerationService

warnings.filterwarnings('ignore')

try:
    import gurobipy as gp
    from gurobipy import GRB
    GUROBI_AVAILABLE = True
except ImportError:
    gp = None  # 设置为 None 以避免 NameError
    GRB = None
    GUROBI_AVAILABLE = False
    print("⚠️  警告: gurobipy 未安装，优化功能将不可用")


class EnergyOptimizer:
    """
    能源优化器
    
    使用混合整数规划 (MIP) 优化电池储能系统的充放电调度
    目标: 最小化总购电成本
    """
    
    def __init__(
        self,
        battery_capacity: float = 60.0,
        max_power: float = 20.0,
        efficiency: float = 0.95
    ):
        """
        初始化优化器
        
        Args:
            battery_capacity: 电池容量 (kWh)，默认 60.0 (工业级储能)
            max_power: 最大充放电功率 (kW)，默认 20.0
            efficiency: 充放电效率，默认 0.95 (95%)
        """
        if not GUROBI_AVAILABLE:
            raise ImportError(
                "gurobipy 未安装。请运行: pip install gurobipy"
            )
        
        # 电池参数
        self.battery_capacity = battery_capacity
        self.max_power = max_power
        self.efficiency = efficiency
        
        # Gurobi 环境
        self.env = None
        
        print(f"⚡ 电池参数:")
        print(f"   - 容量: {battery_capacity} kWh")
        print(f"   - 最大功率: {max_power} kW")
        print(f"   - 效率: {efficiency * 100}%")
    
    def _create_gurobi_env(self) -> 'gp.Env':
        """
        创建 Gurobi 环境
        
        支持 WLS (Web License Service) 和本地许可证
        
        Returns:
            Gurobi 环境对象
            
        Raises:
            Exception: 许可证错误
        """
        try:
            # 检查 WLS 环境变量（使用 secrets 模块统一管理）
            wls_access_id = get_secret('GRB_WLSACCESSID')
            wls_secret = get_secret('GRB_WLSSECRET')
            wls_license_id = get_secret('GRB_LICENSEID')
            
            if wls_access_id and wls_secret:
                print("🔐 使用 WLS (Web License Service) 许可证")
                
                # 创建 WLS 环境
                env = gp.Env(empty=True)
                env.setParam('WLSACCESSID', wls_access_id)
                env.setParam('WLSSECRET', wls_secret)
                
                if wls_license_id:
                    env.setParam('LICENSEID', int(wls_license_id))
                
                env.start()
                print("   ✓ WLS 许可证验证成功")
                
            else:
                print("🔐 使用本地许可证 (或 Size-Limited Trial)")
                
                # 使用默认环境
                env = gp.Env()
                print("   ✓ 许可证验证成功")
            
            return env
            
        except gp.GurobiError as e:
            error_msg = str(e)
            
            if "No Gurobi license found" in error_msg or "license" in error_msg.lower():
                raise Exception(
                    "❌ Gurobi 许可证未找到或无效\n"
                    "   请执行以下步骤之一:\n"
                    "   1. 申请免费学术许可证: https://www.gurobi.com/academia/\n"
                    "   2. 使用 Size-Limited Trial (自动激活，限制 2000 变量)\n"
                    "   3. 配置 WLS 许可证环境变量:\n"
                    "      export GRB_WLSACCESSID=your_access_id\n"
                    "      export GRB_WLSSECRET=your_secret\n"
                    f"   原始错误: {error_msg}"
                )
            else:
                raise Exception(f"Gurobi 环境创建失败: {error_msg}")
    
    def optimize_schedule(
        self,
        load_profile: List[float],
        price_profile: List[float],
        initial_soc: float = 0.5
    ) -> Dict:
        """
        优化电池充放电调度
        
        Args:
            load_profile: 未来24小时的负载预测 (kW)
            price_profile: 未来24小时的电价 (元/kWh)
            initial_soc: 初始电池电量百分比 (0.0-1.0)
            
        Returns:
            优化结果字典，包含:
                - status: 求解状态
                - schedule: 详细调度计划
                - total_cost_without_battery: 无电池时的总成本
                - total_cost_with_battery: 有电池时的总成本
                - savings: 节省金额
                
        Raises:
            ValueError: 输入参数错误
            Exception: 优化失败
        """
        print("\n" + "="*80)
        print("🔧 开始优化电池调度")
        print("="*80 + "\n")
        
        # 验证输入
        if len(load_profile) != 24:
            raise ValueError(f"负载数据长度必须为24，当前为 {len(load_profile)}")
        
        if len(price_profile) != 24:
            raise ValueError(f"电价数据长度必须为24，当前为 {len(price_profile)}")
        
        if not 0 <= initial_soc <= 1:
            raise ValueError(f"初始SOC必须在 [0, 1] 范围内，当前为 {initial_soc}")
        
        # 转换为 numpy 数组
        load = np.array(load_profile)
        price = np.array(price_profile)
        
        print(f"📊 输入数据:")
        print(f"   - 负载范围: {load.min():.2f} - {load.max():.2f} kW")
        print(f"   - 电价范围: {price.min():.2f} - {price.max():.2f} 元/kWh")
        print(f"   - 初始 SOC: {initial_soc * 100:.1f}%")
        
        # 计算无电池时的总成本
        cost_without_battery = np.sum(load * price)
        print(f"   - 无电池总成本: {cost_without_battery:.2f} 元")
        
        try:
            # 创建 Gurobi 环境
            if self.env is None:
                self.env = self._create_gurobi_env()
            
            # 创建模型
            print(f"\n🏗️  构建优化模型...")
            model = gp.Model("BatteryScheduling", env=self.env)
            model.setParam('OutputFlag', 0)  # 关闭求解器输出
            
            # ================================================================
            # Phase 2 新增: 超时与容差参数 (防止计算阻塞)
            # ================================================================
            time_limit = getattr(self, 'time_limit', 60)  # 默认 60 秒
            mip_gap = getattr(self, 'mip_gap', 0.05)  # 默认 5% 误差接受
            model.setParam('TimeLimit', time_limit)
            model.setParam('MIPGap', mip_gap)
            print(f"   ⚙️  求解参数: TimeLimit={time_limit}s, MIPGap={mip_gap*100}%")
            
            T = 24  # 时间步数
            
            # 决策变量
            print(f"   - 创建决策变量...")
            
            # 充电功率 (kW)
            P_charge = model.addVars(T, lb=0, ub=self.max_power, name="P_charge")
            
            # 放电功率 (kW)
            P_discharge = model.addVars(T, lb=0, ub=self.max_power, name="P_discharge")
            
            # 电池存储电量 (kWh)
            E_stored = model.addVars(T, lb=0, ub=self.battery_capacity, name="E_stored")
            
            # 二进制变量: 是否充电
            Is_charge = model.addVars(T, vtype=GRB.BINARY, name="Is_charge")
            
            # 二进制变量: 是否放电
            Is_discharge = model.addVars(T, vtype=GRB.BINARY, name="Is_discharge")
            
            print(f"   ✓ 变量数量: {T * 5} 个")
            
            # 约束条件
            print(f"   - 添加约束条件...")
            
            # 1. 状态互斥约束: 不能同时充放电
            for t in range(T):
                model.addConstr(
                    Is_charge[t] + Is_discharge[t] <= 1,
                    name=f"mutex_{t}"
                )
            
            # 2. 功率限制约束
            for t in range(T):
                # 充电功率限制
                model.addConstr(
                    P_charge[t] <= self.max_power * Is_charge[t],
                    name=f"charge_limit_{t}"
                )
                
                # 放电功率限制
                model.addConstr(
                    P_discharge[t] <= self.max_power * Is_discharge[t],
                    name=f"discharge_limit_{t}"
                )
            
            # 3. 能量守恒约束 (电池动态方程)
            # 单位检查 (防止 MW 数据被当作 kW 使用)
            avg_load = float(np.mean(load_profile))
            if avg_load > 10000:
                # logger.error(f"异常巨大的负载数值 ({avg_load:.2f} kW). 疑似单位错误 (MW vs kW).") # Assuming logger is defined
                # 严重警告，但不阻止运行 (可能会得到不合理的优化结果)
                print(f"⚠️  警告: 检测到非常大的负载 ({avg_load:.2f})，请确认单位是否为 kW")
                raise ValueError(
                    f"检测到异常巨大的负载数值 ({avg_load:.2f} kW)。"
                    "这可能表示单位错误 (例如，输入的是 MW 而非 kW)。"
                    "请确保负载数据以 kW 为单位。"
                )
            
            # 4. 防逆流约束 (No Grid Export)
            # 确保: grid_power = load + charge - discharge >= 0
            # 即: discharge <= load + charge
            # 用户反馈负值是不合理的，因此我们默认开启"防逆流"模式，禁止向电网卖电
            for t in range(T):
                model.addConstr(
                    load[t] + P_charge[t] - P_discharge[t] >= 0,
                    name=f"no_export_{t}"
                )
            
            initial_energy = initial_soc * self.battery_capacity
            
            for t in range(T):
                if t == 0:
                    # 初始时刻
                    model.addConstr(
                        E_stored[t] == initial_energy + 
                        P_charge[t] * self.efficiency - 
                        P_discharge[t] / self.efficiency,
                        name=f"energy_balance_{t}"
                    )
                else:
                    # 后续时刻
                    model.addConstr(
                        E_stored[t] == E_stored[t-1] + 
                        P_charge[t] * self.efficiency - 
                        P_discharge[t] / self.efficiency,
                        name=f"energy_balance_{t}"
                    )
            
            print(f"   ✓ 约束数量: {T * 4} 个")
            
            # 目标函数: 最小化总购电成本
            print(f"   - 设置目标函数...")
            
            total_cost = gp.quicksum(
                (load[t] + P_charge[t] - P_discharge[t]) * price[t]
                for t in range(T)
            )
            
            model.setObjective(total_cost, GRB.MINIMIZE)
            print(f"   ✓ 目标: 最小化总购电成本")
            
            # 求解模型
            print(f"\n🚀 开始求解...")
            model.optimize()
            
            # 检查求解状态
            status = model.status
            
            if status == GRB.OPTIMAL:
                print(f"   ✓ 求解成功! (状态: OPTIMAL)")
                
                # 提取结果
                schedule = []
                soc_hits_min = 0
                soc_hits_max = 0
                charge_hits = 0
                discharge_hits = 0
                
                for t in range(T):
                    p_charge = P_charge[t].X
                    p_discharge = P_discharge[t].X
                    e_stored = E_stored[t].X
                    soc = e_stored / self.battery_capacity

                    if soc <= 0.10 + 1e-6:
                        soc_hits_min += 1
                    if soc >= 0.90 - 1e-6:
                        soc_hits_max += 1
                    if abs(p_charge - self.max_power) < 1e-5 and p_charge > 0:
                        charge_hits += 1
                    if abs(p_discharge - self.max_power) < 1e-5 and p_discharge > 0:
                        discharge_hits += 1
                    
                    # 记录调度结果 (kW)
                    # grid_power = load + charge - discharge
                    # 正值 = 从电网买电, 负值 = 向电网卖电
                    grid_power = load[t] + p_charge - p_discharge
                    
                    schedule.append({
                        'hour': t,
                        'load': float(load[t]),
                        'price': float(price[t]),
                        'charge_power': float(p_charge),
                        'discharge_power': float(p_discharge),
                        'battery_action': float(p_charge - p_discharge),
                        'soc': float(soc),
                        'stored_energy': float(e_stored),
                        'grid_power': float(grid_power)
                    })
                    
                # 检查是否存在大量反向送电 (Export)
                total_export = sum(max(0, -item['grid_power']) for item in schedule)
                if total_export > 1000: # 如果全天送电超过 1000 kWh (5MW 电池容易跑到这个值)
                    print(f"⚠️ 注意: 检测到大量反向送电 ({total_export:.2f} kWh)。")
                    print("   如果这不是预期的，请检查电池容量设置是否过大 (MW级别?)")
                
                # 计算总成本
                cost_with_battery = model.objVal
                savings = cost_without_battery - cost_with_battery
                savings_percent = (savings / cost_without_battery) * 100 if cost_without_battery > 0 else 0
                
                print(f"\n📊 优化结果:")
                print(f"   - 无电池总成本: {cost_without_battery:.2f} 元")
                print(f"   - 有电池总成本: {cost_with_battery:.2f} 元")
                print(f"   - 节省金额: {savings:.2f} 元 ({savings_percent:.1f}%)")

                diagnostics = {
                    'runtime_sec': float(getattr(model, "Runtime", 0.0)),
                    'mip_gap': float(getattr(model, "MIPGap", 0.0)) if hasattr(model, "MIPGap") else None,
                    'node_count': int(getattr(model, "NodeCount", 0)) if hasattr(model, "NodeCount") else None,
                    'iter_count': int(getattr(model, "IterCount", 0)) if hasattr(model, "IterCount") else None,
                }

                constraint_hits = {
                    'soc_min_hits': soc_hits_min,
                    'soc_max_hits': soc_hits_max,
                    'max_charge_hits': charge_hits,
                    'max_discharge_hits': discharge_hits
                }
                
                return {
                    'status': 'Optimal',
                    'schedule': schedule,
                    'total_cost_without_battery': float(cost_without_battery),
                    'total_cost_with_battery': float(cost_with_battery),
                    'savings': float(savings),
                    'savings_percent': float(savings_percent),
                    'diagnostics': diagnostics,
                    'constraint_hits': constraint_hits
                }
                
            elif status == GRB.INFEASIBLE:
                print(f"   ❌ 模型不可行 (INFEASIBLE)")
                return {
                    'status': 'Infeasible',
                    'error': '模型约束不可行，请检查输入参数'
                }
                
            elif status == GRB.UNBOUNDED:
                print(f"   ❌ 模型无界 (UNBOUNDED)")
                return {
                    'status': 'Unbounded',
                    'error': '模型目标函数无界'
                }
                
            else:
                # ================================================================
                # Phase 2 新增: 超时降级处理
                # ================================================================
                if status == GRB.TIME_LIMIT:
                    print(f"   ⚠️  求解超时，启用贪心降级算法...")
                    fallback_result = self._greedy_fallback(load_profile, price_profile, initial_soc)
                    fallback_result['status'] = 'Timeout_Fallback'
                    fallback_result['warning'] = f'求解超时 ({time_limit}s)，使用贪心算法近似解'
                    return fallback_result
                
                print(f"   ⚠️  求解未完成 (状态码: {status})")
                return {
                    'status': 'Unknown',
                    'error': f'求解状态未知 (状态码: {status})'
                }
                
        except gp.GurobiError as e:
            error_msg = str(e)
            
            if "license" in error_msg.lower():
                print(f"\n❌ Gurobi 许可证错误")
                return {
                    'status': 'Error',
                    'error': 'Optimization failed: Gurobi license not found'
                }
            else:
                print(f"\n❌ Gurobi 错误: {error_msg}")
                return {
                    'status': 'Error',
                    'error': f'Gurobi error: {error_msg}'
                }
                
        except Exception as e:
            print(f"\n❌ 优化失败: {str(e)}")
            return {
                'status': 'Error',
                'error': str(e)
            }
    
    def print_schedule(self, result: Dict):
        """
        打印优化调度结果
        
        Args:
            result: optimize_schedule 返回的结果字典
        """
        if result['status'] != 'Optimal':
            print(f"\n❌ 优化失败: {result.get('error', 'Unknown error')}")
            return
        
        print("\n" + "="*80)
        print("📅 优化调度计划")
        print("="*80 + "\n")
        
        schedule = result['schedule']
        
        # 打印表头
        print(f"{'时间':<6} {'负载':<10} {'电价':<10} {'电池动作':<12} {'SOC':<10} {'说明':<15}")
        print("-" * 80)
        
        for item in schedule:
            hour = item['hour']
            load = item['load']
            price = item['price']
            action = item['battery_action']
            soc = item['soc']
            
            # 判断电池动作
            if abs(action) < 0.01:
                action_str = "待机"
                action_val = "0.00 kW"
            elif action > 0:
                action_str = "充电"
                action_val = f"+{action:.2f} kW"
            else:
                action_str = "放电"
                action_val = f"{action:.2f} kW"
            
            # 判断电价时段
            if price <= 0.3:
                period = "谷时"
            elif price <= 0.6:
                period = "平时"
            else:
                period = "峰时"
            
            print(f"{hour:02d}:00  {load:>6.2f} kW  {price:>6.2f}元  {action_val:<12} {soc*100:>5.1f}%  {action_str} ({period})")
        
        # 打印总结
        print("\n" + "-" * 80)
        print(f"💰 成本分析:")
        print(f"   - 无电池总成本: {result['total_cost_without_battery']:.2f} 元")
        print(f"   - 有电池总成本: {result['total_cost_with_battery']:.2f} 元")
        print(f"   - 节省金额: {result['savings']:.2f} 元 ({result['savings_percent']:.1f}%)")
        print("="*80 + "\n")
    
    def close(self):
        """显式关闭 Gurobi 环境（推荐在使用完毕后调用）"""
        if self.env is not None:
            try:
                self.env.dispose()
                self.env = None
                print("🧹 Gurobi 环境已关闭")
            except Exception as e:
                print(f"⚠️ 关闭 Gurobi 环境时出错: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口 - 自动关闭环境"""
        self.close()
        return False
    
    def __del__(self):
        """析构函数: 关闭 Gurobi 环境（兜底）"""
        self.close()
    
    # ================================================================
    # Phase 2 新增: 贪心降级算法
    # ================================================================
    def _greedy_fallback(
        self,
        load_profile: List[float],
        price_profile: List[float],
        initial_soc: float = 0.5
    ) -> Dict:
        """
        贪心降级算法 (当 Gurobi 超时或不可用时使用)
        
        策略:
        - 谷时充电 (电价 < 0.4)
        - 峰时放电 (电价 > 0.8)
        - 其他时段待机
        
        Args:
            load_profile: 负载预测 (kW)
            price_profile: 电价 (元/kWh)
            initial_soc: 初始电量百分比
            
        Returns:
            近似优化结果
        """
        print("   🔄 执行贪心降级算法...")
        
        T = len(load_profile)
        load = np.array(load_profile)
        price = np.array(price_profile)
        
        # 电池状态
        soc = initial_soc
        energy = soc * self.battery_capacity
        
        schedule = []
        total_cost = 0.0
        
        for t in range(T):
            p_charge = 0.0
            p_discharge = 0.0
            
            # 谷时充电 (电价低)
            if price[t] <= 0.4 and energy < self.battery_capacity * 0.9:
                # 充电，但不超过最大功率和容量限制
                max_charge = min(
                    self.max_power,
                    (self.battery_capacity * 0.9 - energy) / self.efficiency
                )
                p_charge = max_charge
                energy += p_charge * self.efficiency
            
            # 峰时放电 (电价高)
            elif price[t] >= 0.8 and energy > self.battery_capacity * 0.1:
                # 放电，但不超过最大功率、当前负载和电量限制
                max_discharge = min(
                    self.max_power,
                    load[t],  # 不能超过负载 (防逆流)
                    (energy - self.battery_capacity * 0.1) * self.efficiency
                )
                p_discharge = max_discharge
                energy -= p_discharge / self.efficiency
            
            # 计算电网功率和成本
            grid_power = load[t] + p_charge - p_discharge
            cost = grid_power * price[t]
            total_cost += cost
            
            soc = energy / self.battery_capacity
            
            schedule.append({
                'hour': t,
                'load': float(load[t]),
                'price': float(price[t]),
                'charge_power': float(p_charge),
                'discharge_power': float(p_discharge),
                'battery_action': float(p_charge - p_discharge),
                'soc': float(soc),
                'stored_energy': float(energy),
                'grid_power': float(grid_power)
            })
        
        # 计算节省
        cost_without_battery = np.sum(load * price)
        savings = cost_without_battery - total_cost
        savings_percent = (savings / cost_without_battery) * 100 if cost_without_battery > 0 else 0
        
        print(f"   ✓ 贪心算法完成: 节省 {savings:.2f} 元 ({savings_percent:.1f}%)")
        
        return {
            'status': 'Greedy_Fallback',
            'schedule': schedule,
            'total_cost_without_battery': float(cost_without_battery),
            'total_cost_with_battery': float(total_cost),
            'savings': float(savings),
            'savings_percent': float(savings_percent),
            'algorithm': 'greedy'
        }
    
    # ================================================================
    # Phase 2 新增: 批量敏感性分析
    # ================================================================
    def simulate_scenarios(
        self,
        load_profile: List[float],
        price_profile: List[float],
        variations: Optional[Dict[str, List]] = None,
        profile_context: str = 'scenario_simulation',
    ) -> List[Dict]:
        """
        批量模拟多种参数配置的敏感性分析
        
        Args:
            load_profile: 基准负载预测
            price_profile: 基准电价
            variations: 参数变化字典，例如:
                {
                    'battery_capacity': [10, 20, 50],
                    'max_power': [5, 10, 20]
                }
                
        Returns:
            每种配置的优化结果列表
        """
        if variations is None:
            # 默认敏感性分析范围
            variations = {
                'battery_capacity': [self.battery_capacity * 0.5, self.battery_capacity, self.battery_capacity * 1.5],
                'max_power': [self.max_power * 0.5, self.max_power, self.max_power * 1.5]
            }
        
        started_at = perf_counter()
        results = []
        original_capacity = self.battery_capacity
        original_power = self.max_power
        
        print(f"\n📊 开始敏感性分析...")
        print(f"   参数范围:")
        for param, values in variations.items():
            print(f"   - {param}: {values}")
        
        # 生成所有参数组合
        from itertools import product
        
        param_names = list(variations.keys())
        param_values = list(variations.values())
        
        for combo in product(*param_values):
            # 设置参数
            params = dict(zip(param_names, combo))
            
            if 'battery_capacity' in params:
                self.battery_capacity = params['battery_capacity']
            if 'max_power' in params:
                self.max_power = params['max_power']
            
            print(f"\n   🔄 测试配置: {params}")
            
            try:
                # 使用贪心算法快速模拟 (避免每次都调用 Gurobi)
                result = self._greedy_fallback(load_profile, price_profile)
                result['params'] = params
                results.append(result)
                
                print(f"      节省: {result['savings']:.2f} 元 ({result['savings_percent']:.1f}%)")
                
            except Exception as e:
                results.append({
                    'params': params,
                    'status': 'Error',
                    'error': str(e)
                })
        
        # 恢复原始参数
        self.battery_capacity = original_capacity
        self.max_power = original_power
        
        # 按节省金额排序
        results.sort(key=lambda x: x.get('savings', 0), reverse=True)
        
        print(f"\n✅ 敏感性分析完成: {len(results)} 种配置")
        if results and results[0].get('savings'):
            best = results[0]
            print(f"   🏆 最佳配置: {best['params']}, 节省 {best['savings']:.2f} 元")

        duration_ms = (perf_counter() - started_at) * 1000.0
        ComputeAccelerationService.record_component_sample(
            component='scenario_simulation',
            duration_ms=duration_ms,
            rows=len(results),
            backend='python_numpy',
            context=profile_context,
            native_enabled=False,
            native_available=False,
            preferred_backend='python_numpy',
            metadata={
                'load_points': len(load_profile),
                'price_points': len(price_profile),
                'scenario_count': len(results),
                'variation_keys': param_names,
            },
        )
        print(f"   ✓ 情景模拟耗时: {duration_ms:.2f} ms")
        
        return results

