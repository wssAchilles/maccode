
import os
import sys
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("VerifyWorkflow")

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'back')))

# 设置凭证路径
KEY_PATH = "/Users/achilles/Documents/code/data science/service-account-key.json"
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = KEY_PATH
os.environ['GCP_PROJECT_ID'] = 'data-science-44398'  # 从之前的输出获知
os.environ['STORAGE_BUCKET_NAME'] = 'data-science-44398.firebasestorage.app' # 假设默认 bucket
# 注意：如果 config.py 里有其他必需环境变量，可能需要在此设置
# 比如 OPENWEATHER_API_KEY，需要确保它能被读取 (从 .env 或直接设置)
# 这里假设它已经在环境变量中或者 config.py 能够处理 (用户本地可能有 .env)
# 之前的 view_file app.yaml 显示了 OPENWEATHER_API_KEY 在 app.yaml env_variables 里
# 本地运行时，我们需要手动设置它，除非 dotenv 能加载
os.environ['OPENWEATHER_API_KEY'] = "e8f11d28ce6faf3a9aa93828fb8fbff1" 

def verify_data_fetching():
    logger.info("="*60)
    logger.info("🧪 测试任务 1: 每小时数据抓取 (Data Fetching)")
    logger.info("="*60)
    
    try:
        from back.services.external_data_service import ExternalDataService
        
        service = ExternalDataService()
        logger.info("1. ExternalDataService 初始化成功")
        
        logger.info("2. 执行 fetch_and_publish()...")
        success = service.fetch_and_publish()
        
        if success:
            logger.info("✅ 数据抓取成功！数据已保存到 Firebase Storage。")
            return True
        else:
            logger.error("❌ 数据抓取返回失败。")
            return False
            
    except Exception as e:
        logger.error(f"❌ 数据抓取过程发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_model_training():
    logger.info("\n" + "="*60)
    logger.info("🧪 测试任务 2: 每日模型训练 (Model Training)")
    logger.info("="*60)
    
    try:
        from back.services.ml_service import EnergyPredictor
        
        predictor = EnergyPredictor()
        logger.info("1. EnergyPredictor 初始化成功")
        
        logger.info("2. 执行 train_model(use_firebase_storage=True)...")
        # 为了不消耗太多时间，我们可以减少 n_estimators，但为了完整验证，保持默认或稍减
        metrics = predictor.train_model(
            use_firebase_storage=True,
            n_estimators=50 # 稍微减少以加快测试速度，但足够验证流程
        )
        
        logger.info("✅ 模型训练成功！")
        logger.info(f"   MAE: {metrics.get('test_mae')}")
        logger.info(f"   RMSE: {metrics.get('test_rmse')}")
        logger.info("   模型文件已更新到 Firebase Storage。")
        return True
        
    except Exception as e:
        logger.error(f"❌ 模型训练过程发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if not os.path.exists(KEY_PATH):
        logger.error(f"❌ 找不到凭证文件: {KEY_PATH}")
        sys.exit(1)
        
    print(f"🔑 使用凭证: {KEY_PATH}")
    
    # 验证数据抓取
    fetch_ok = verify_data_fetching()
    
    # 验证模型训练
    train_ok = False
    if fetch_ok:
        train_ok = verify_model_training()
    else:
        logger.warning("⚠️ 跳过模型训练测试，因为数据抓取失败。")
    
    print("\n" + "="*60)
    if fetch_ok and train_ok:
        print("✅✅ 全部验证通过！您的生产工作流在本地测试正常。")
    else:
        print("❌⚠️ 验证存在问题，请检查日志。")
