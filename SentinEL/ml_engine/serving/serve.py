import os
import json
import torch
import logging
import sys
from fastapi import FastAPI, Request, Response, status
from ml_engine.models.churn_transformer import MultimodalChurnTransformer

# 配置日志 - 同时输出到 stdout 以确保 Cloud Logging 捕获
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()
model = None
device = torch.device("cpu")
config = {}

def get_model_dir():
    # 优先使用镜像内预置的模型
    if os.path.exists("/app/model/model.pt"):
        return "/app/model"
    # 其次使用 Vertex AI 传入的 URI
    uri = os.environ.get("AIP_STORAGE_URI")
    if uri and uri.strip():
        return uri
    return "/app/model"

def load_model_logic():
    global model, config, device
    try:
        model_dir = get_model_dir()
        logger.info(f"Attempting to load model from: {model_dir}")
        
        config_path = os.path.join(model_dir, "model_config.json")
        weights_path = os.path.join(model_dir, "model.pt")
        
        if not os.path.exists(config_path):
            logger.error(f"Config file not found: {config_path}")
            # Debug: List directory content
            if os.path.exists(model_dir):
                logger.info(f"Contents of {model_dir}: {os.listdir(model_dir)}")
            else:
                logger.error(f"Directory {model_dir} does not exist")
            return False

        if not os.path.exists(weights_path):
            logger.error(f"Weights file not found: {weights_path}")
            return False

        with open(config_path, "r") as f:
            config = json.load(f)
            
        logger.info(f"Loaded config: {config}")
        
        # 过滤掉不需要的配置项 (如 metadata: best_auc, trial_id 等)
        import inspect
        sig = inspect.signature(MultimodalChurnTransformer)
        valid_keys = set(sig.parameters.keys())
        clean_config = {k: v for k, v in config.items() if k in valid_keys}
        
        if len(clean_config) < len(config):
            logger.info(f"Filtered config keys. Removed: {set(config.keys()) - set(clean_config.keys())}")
            
        model_instance = MultimodalChurnTransformer(**clean_config)
        model_instance.load_state_dict(torch.load(weights_path, map_location=device))
        model_instance.to(device)
        model_instance.eval()
        
        model = model_instance
        logger.info("Model loaded successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}", exc_info=True)
        return False

@app.on_event("startup")
def startup_event():
    load_model_logic()

@app.get("/health")
def health(response: Response):
    if model is None:
        # Try lazy load
        if load_model_logic():
             return {"status": "healthy", "msg": "Lazy loaded"}
        
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "reason": "Model not loaded"}
    return {"status": "healthy"}

@app.get("/debug")
def debug_info():
    """Debug endpoint to inspect environment and filesystem"""
    try:
        model_dir = get_model_dir()
        files = []
        if os.path.exists(model_dir):
            files = os.listdir(model_dir)
        
        return {
            "env": dict(os.environ),
            "model_dir": model_dir,
            "model_dir_exists": os.path.exists(model_dir),
            "model_dir_files": files,
            "cwd": os.getcwd(),
            "cwd_files": os.listdir(".") if os.path.exists(".") else [],
            "app_files": os.listdir("/app") if os.path.exists("/app") else []
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/predict")
async def predict(request: Request):
    global model
    if not model:
        logger.warning("Model is None in predict, attempting lazy load...")
        if not load_model_logic():
            return {"error": "Model not loaded"}
        
    try:
        body = await request.json()
    except Exception:
        return {"error": "Invalid JSON body"}
        
    instances = body.get("instances", [])
    if not instances:
        return {"predictions": []}
        
    # 预处理
    event_seqs = []
    for inst in instances:
        seq = inst.get("sequence", [])
        # 简单校验
        if not isinstance(seq, list):
             # 容错处理
             seq = [0] * config.get('max_seq_len', 20)
        event_seqs.append(seq)
    
    # 转换为 Tensor
    try:
        event_tensor = torch.tensor(event_seqs, dtype=torch.long).to(device)
        
        batch_size = len(event_seqs)
        
        # 构造 Dummy Features (全 0)
        # 类别特征
        num_cat = len(config.get('cat_feature_dims', []))
        static_cat = torch.zeros((batch_size, num_cat), dtype=torch.long).to(device)
        
        # 数值特征
        num_num = config.get('num_numerical_features', 0)
        static_num = torch.zeros((batch_size, num_num), dtype=torch.float32).to(device)
        
        with torch.no_grad():
            preds = model(event_tensor, static_cat, static_num)
            
        return {"predictions": preds.squeeze(1).tolist()}
        
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Vertex AI Custom Container 默认监听 8080
    uvicorn.run(app, host="0.0.0.0", port=8080)
