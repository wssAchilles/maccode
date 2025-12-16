"""
能源优化服务模块 - 电池储能系统优化调度
Energy Optimization Service - Battery Energy Storage System Scheduling

使用 Gurobi 求解器进行混合整数规划 (MIP) 优化
"""

import os
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
import warnings

from services.secrets import get_secret

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
                
                for t in range(T):
                    p_charge = P_charge[t].X
                    p_discharge = P_discharge[t].X
                    e_stored = E_stored[t].X
                    soc = e_stored / self.battery_capacity
                    
                    # battery_action: 正值为充电，负值为放电
                    battery_action = p_charge - p_discharge
                    
                    schedule.append({
                        'hour': t,
                        'load': float(load[t]),
                        'price': float(price[t]),
                        'battery_action': float(battery_action),
                        'charge_power': float(p_charge),
                        'discharge_power': float(p_discharge),
                        'soc': float(soc),
                        'stored_energy': float(e_stored)
                    })
                
                # 计算总成本
                cost_with_battery = model.objVal
                savings = cost_without_battery - cost_with_battery
                savings_percent = (savings / cost_without_battery) * 100 if cost_without_battery > 0 else 0
                
                print(f"\n📊 优化结果:")
                print(f"   - 无电池总成本: {cost_without_battery:.2f} 元")
                print(f"   - 有电池总成本: {cost_with_battery:.2f} 元")
                print(f"   - 节省金额: {savings:.2f} 元 ({savings_percent:.1f}%)")
                
                return {
                    'status': 'Optimal',
                    'schedule': schedule,
                    'total_cost_without_battery': float(cost_without_battery),
                    'total_cost_with_battery': float(cost_with_battery),
                    'savings': float(savings),
                    'savings_percent': float(savings_percent)
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



