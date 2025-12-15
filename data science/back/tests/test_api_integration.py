"""
API 测试脚本
测试优化 API 接口
"""

import requests
import json
from datetime import datetime, timedelta

# 配置
BASE_URL = "http://localhost:8080"
# 注意: 实际使用时需要 Firebase Token，这里先测试不需要认证的接口


def test_get_config():
    """测试获取配置接口"""
    print("\n" + "="*80)
    print("测试 1: GET /api/optimization/config")
    print("="*80)
    
    url = f"{BASE_URL}/api/optimization/config"
    
    try:
        response = requests.get(url)
        
        print(f"状态码: {response.status_code}")
        print(f"响应:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        if response.status_code == 200:
            print("✅ 测试通过")
        else:
            print("❌ 测试失败")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return False


def test_run_optimization_no_auth():
    """测试优化接口（无认证，预期失败）"""
    print("\n" + "="*80)
    print("测试 2: POST /api/optimization/run (无认证)")
    print("="*80)
    
    url = f"{BASE_URL}/api/optimization/run"
    
    payload = {
        "initial_soc": 0.5,
        "target_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    }
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"状态码: {response.status_code}")
        print(f"响应:")
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
        # 预期返回 401 (未认证)
        if response.status_code == 401:
            print("✅ 测试通过 (正确拒绝未认证请求)")
            return True
        else:
            print("⚠️  预期返回 401，实际返回", response.status_code)
            return False
        
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return False


def test_run_optimization_with_mock_auth():
    """测试优化接口（模拟认证）"""
    print("\n" + "="*80)
    print("测试 3: POST /api/optimization/run (模拟认证)")
    print("="*80)
    print("⚠️  注意: 此测试需要有效的 Firebase Token")
    print("如果没有 Token，请跳过此测试")
    
    url = f"{BASE_URL}/api/optimization/run"
    
    # 这里需要真实的 Firebase ID Token
    # 可以从前端获取或使用 Firebase Admin SDK 生成
    token = input("\n请输入 Firebase ID Token (直接回车跳过): ").strip()
    
    if not token:
        print("⏭️  跳过测试")
        return None
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "initial_soc": 0.5,
        "target_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
        "temperature_forecast": [
            24.0, 23.5, 23.0, 22.8, 22.5, 23.0,
            24.0, 25.0, 26.5, 28.0, 29.5, 30.5,
            31.0, 31.5, 31.8, 31.5, 31.0, 30.0,
            28.5, 27.0, 26.0, 25.5, 25.0, 24.5
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ 优化成功!")
            print(f"\n优化摘要:")
            summary = result.get('optimization', {}).get('summary', {})
            print(f"  - 无电池成本: {summary.get('total_cost_without_battery', 0):.2f} 元")
            print(f"  - 有电池成本: {summary.get('total_cost_with_battery', 0):.2f} 元")
            print(f"  - 节省金额: {summary.get('savings', 0):.2f} 元")
            print(f"  - 节省比例: {summary.get('savings_percent', 0):.1f}%")
            
            strategy = result.get('optimization', {}).get('strategy', {})
            print(f"\n充放电策略:")
            print(f"  - 充电时段: {strategy.get('charging_hours', [])}")
            print(f"  - 放电时段: {strategy.get('discharging_hours', [])}")
            
            # 保存完整结果
            with open('optimization_result.json', 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\n完整结果已保存到: optimization_result.json")
            
            return True
        else:
            print(f"\n❌ 优化失败")
            print(f"响应:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return False
        
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_simulate_scenario_no_auth():
    """测试场景模拟接口（无认证，预期失败）"""
    print("\n" + "="*80)
    print("测试 4: POST /api/optimization/simulate (无认证)")
    print("="*80)
    
    url = f"{BASE_URL}/api/optimization/simulate"
    
    payload = {
        "target_date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    }
    
    try:
        response = requests.post(url, json=payload)
        
        print(f"状态码: {response.status_code}")
        
        # 预期返回 401
        if response.status_code == 401:
            print("✅ 测试通过 (正确拒绝未认证请求)")
            return True
        else:
            print("⚠️  预期返回 401，实际返回", response.status_code)
            return False
        
    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return False


def check_server():
    """检查服务器是否运行"""
    print("\n" + "="*80)
    print("检查服务器状态")
    print("="*80)
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        
        if response.status_code == 200:
            print(f"✅ 服务器运行正常")
            print(f"响应: {response.json()}")
            return True
        else:
            print(f"⚠️  服务器响应异常: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到服务器: {BASE_URL}")
        print(f"请确保服务器正在运行:")
        print(f"  cd /Users/achilles/Documents/code/data\\ science/back")
        print(f"  python main.py")
        return False
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    print("\n" + "🧪 " + "="*76)
    print("优化 API 测试套件")
    print("="*78)
    
    # 检查服务器
    if not check_server():
        print("\n❌ 服务器未运行，测试终止")
        return
    
    # 运行测试
    results = []
    
    # 测试 1: 获取配置
    results.append(("GET /api/optimization/config", test_get_config()))
    
    # 测试 2: 优化接口（无认证）
    results.append(("POST /api/optimization/run (无认证)", test_run_optimization_no_auth()))
    
    # 测试 3: 优化接口（有认证）
    result = test_run_optimization_with_mock_auth()
    if result is not None:
        results.append(("POST /api/optimization/run (有认证)", result))
    
    # 测试 4: 场景模拟（无认证）
    results.append(("POST /api/optimization/simulate (无认证)", test_simulate_scenario_no_auth()))
    
    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
    
    print("\n" + "="*80)
    print("下一步:")
    print("  1. 使用 Firebase Authentication 获取真实 Token")
    print("  2. 测试完整的优化流程")
    print("  3. 集成到前端应用")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
