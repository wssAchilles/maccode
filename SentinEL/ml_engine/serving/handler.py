"""
SentinEL LSTM 模型 Handler (TorchServe)
用于 Vertex AI Prediction 的自定义 Handler

TorchServe 要求定义以下方法:
    - initialize: 加载模型
    - preprocess: 预处理输入
    - inference: 执行推理
    - postprocess: 后处理输出
"""

import json
import torch
import logging

logger = logging.getLogger(__name__)


class ChurnLSTMHandler:
    """
    TorchServe Handler for ChurnLSTM
    """
    
    def __init__(self):
        self.model = None
        self.device = None
    
    def initialize(self, context):
        """
        加载模型
        
        Args:
            context: TorchServe context，包含模型路径等信息
        """
        properties = context.system_properties
        model_dir = properties.get("model_dir")
        
        # 设置设备
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 加载 TorchScript 模型
        model_path = f"{model_dir}/model.pt"
        self.model = torch.jit.load(model_path, map_location=self.device)
        self.model.eval()
        
        logger.info(f"Model loaded from {model_path} on {self.device}")
    
    def preprocess(self, data):
        """
        预处理输入数据
        
        Args:
            data: 输入数据列表
            
        Returns:
            torch.Tensor: 预处理后的张量
        """
        sequences = []
        
        for item in data:
            body = item.get("body") or item.get("data") or item
            
            if isinstance(body, bytes):
                body = json.loads(body.decode("utf-8"))
            elif isinstance(body, str):
                body = json.loads(body)
            
            sequence = body.get("sequence", [])
            sequences.append(sequence)
        
        # 转换为张量
        tensor = torch.tensor(sequences, dtype=torch.long, device=self.device)
        return tensor
    
    def inference(self, data):
        """
        执行模型推理
        
        Args:
            data: 预处理后的输入张量
            
        Returns:
            torch.Tensor: 模型输出
        """
        with torch.no_grad():
            output = self.model(data)
        return output
    
    def postprocess(self, data):
        """
        后处理输出
        
        Args:
            data: 模型输出张量
            
        Returns:
            list: JSON 可序列化的结果
        """
        # 转换为 Python 列表
        probabilities = data.squeeze().cpu().tolist()
        
        # 确保是列表格式
        if isinstance(probabilities, float):
            probabilities = [probabilities]
        
        return probabilities


# TorchServe 入口点
_service = ChurnLSTMHandler()


def handle(data, context):
    """
    TorchServe 入口函数
    """
    if not _service.model:
        _service.initialize(context)
    
    if data is None:
        return None
    
    preprocessed = _service.preprocess(data)
    output = _service.inference(preprocessed)
    result = _service.postprocess(output)
    
    return result
