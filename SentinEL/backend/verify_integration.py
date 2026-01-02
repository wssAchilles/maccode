"""
SentinEL Vertex AI 集成验证脚本

验证 Transformer 模型 Endpoint 是否正确工作：
1. 配置加载正确
2. 数据组装格式正确 (Shape/Type)
3. Vertex AI 调用成功
4. 结果解析正确

用法:
    cd backend
    python verify_integration.py
"""

import sys
import os

# 确保项目根目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from google.cloud import aiplatform
from google.cloud.aiplatform import Endpoint

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verify_config():
    """验证配置加载"""
    print("\n" + "=" * 60)
    print("Step 1: 验证配置加载")
    print("=" * 60)
    
    try:
        from app.core.config import settings
        
        print(f"  ✓ PROJECT_ID: {settings.PROJECT_ID}")
        print(f"  ✓ LOCATION: {settings.LOCATION}")
        print(f"  ✓ VERTEX_ENDPOINT_ID: {settings.VERTEX_ENDPOINT_ID}")
        
        return settings
    except Exception as e:
        print(f"  ✗ 配置加载失败: {e}")
        return None


def verify_data_assembly(settings):
    """验证数据组装"""
    print("\n" + "=" * 60)
    print("Step 2: 验证数据组装 (Transformer 三路输入)")
    print("=" * 60)
    
    try:
        from app.services.prediction_service import PredictionService
        
        # 创建服务实例
        service = PredictionService(
            project_id=settings.PROJECT_ID,
            region=settings.LOCATION
        )
        
        # 测试数据组装
        test_user_id = "test_user_12345"
        test_events = ["page_view", "view_item", "add_to_cart", "begin_checkout"]
        
        # 使用内部方法生成输入
        transformer_input = service._assemble_transformer_input(test_user_id, test_events)
        
        print(f"  ✓ sequence: 类型={type(transformer_input['sequence']).__name__}, "
              f"长度={len(transformer_input['sequence'])}")
        print(f"    数据: {transformer_input['sequence']}")
        
        # 验证形状
        assert len(transformer_input['sequence']) == 20, "sequence 长度应为 20"
        
        print("\n  ✓ 数据形状验证通过!")
        
        return service, transformer_input
        
    except Exception as e:
        print(f"  ✗ 数据组装失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def verify_endpoint_call(settings, transformer_input):
    """验证 Vertex AI Endpoint 调用"""
    print("\n" + "=" * 60)
    print("Step 3: 验证 Vertex AI Endpoint 调用")
    print("=" * 60)
    
    try:
        # 初始化 Vertex AI
        aiplatform.init(project=settings.PROJECT_ID, location=settings.LOCATION)
        
        # 通过 ID 获取 Endpoint
        endpoint_id = settings.VERTEX_ENDPOINT_ID
        resource_name = f"projects/{settings.PROJECT_ID}/locations/{settings.LOCATION}/endpoints/{endpoint_id}"
        
        print(f"  → 连接 Endpoint: {resource_name}")
        
        endpoint = Endpoint(endpoint_name=resource_name)
        print(f"  ✓ Endpoint 连接成功")
        
        # 构造请求
        instances = [transformer_input]
        print(f"  → 发送预测请求...")
        print(f"    Instances: {instances}")
        
        # 调用预测
        prediction = endpoint.predict(instances)
        
        print(f"  ✓ 预测请求成功!")
        print(f"    Raw predictions: {prediction.predictions}")
        
        # 解析结果
        if prediction.predictions:
            result = prediction.predictions[0]
            if isinstance(result, list):
                probability = float(result[0])
            else:
                probability = float(result)
            
            print(f"\n  ✓ 预测结果: {probability:.4f}")
            return probability
        else:
            print("  ✗ 无预测结果返回")
            return None
            
    except Exception as e:
        print(f"  ✗ Endpoint 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def verify_prediction_service(settings):
    """验证完整的 PredictionService 流程"""
    print("\n" + "=" * 60)
    print("Step 4: 验证完整 PredictionService 流程")
    print("=" * 60)
    
    try:
        from app.services.prediction_service import get_prediction_service
        
        service = get_prediction_service()
        if service is None:
            print("  ✗ PredictionService 初始化失败")
            return None
        
        print("  ✓ PredictionService 初始化成功")
        
        # 测试预测
        test_user_id = "test_user_12345"
        test_events = ["page_view", "view_item", "add_to_cart", "purchase"]
        
        print(f"  → 调用 predict_churn(user_id='{test_user_id}', events={test_events})")
        
        probability = service.predict_churn(
            user_id=test_user_id,
            events=test_events,
            use_cache=False
        )
        
        print(f"\n  ✓ 预测结果: {probability:.4f}")
        print(f"  ✓ 风险等级: {service.get_risk_level(probability)}")
        
        return probability
        
    except Exception as e:
        print(f"  ✗ PredictionService 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("SentinEL Vertex AI Transformer 集成验证")
    print("=" * 60)
    
    # Step 1: 验证配置
    settings = verify_config()
    if settings is None:
        print("\n❌ 配置验证失败，退出")
        return False
    
    # Step 2: 验证数据组装
    service, transformer_input = verify_data_assembly(settings)
    if transformer_input is None:
        print("\n❌ 数据组装验证失败，退出")
        return False
    
    # Step 3: 验证 Endpoint 调用
    probability = verify_endpoint_call(settings, transformer_input)
    if probability is None:
        print("\n❌ Endpoint 调用验证失败，退出")
        return False
    
    # Step 4: 验证完整服务
    final_probability = verify_prediction_service(settings)
    if final_probability is None:
        print("\n❌ PredictionService 验证失败，退出")
        return False
    
    # 汇总
    print("\n" + "=" * 60)
    print("✅ 所有验证通过!")
    print("=" * 60)
    print(f"  Endpoint ID: {settings.VERTEX_ENDPOINT_ID}")
    print(f"  Region: {settings.LOCATION}")
    print(f"  最终预测概率: {final_probability:.4f}")
    print("=" * 60 + "\n")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
