"""
SentinEL 双塔推荐模型训练脚本 (Two-Tower Model)

模型架构:
1. User Tower (Query Tower):
   - 输入: user_id (Embedding), user_risk_score (Dense)
   - 输出: 32维 Embedding

2. Strategy Tower (Candidate Tower):
   - 输入: strategy_id (Embedding), description (TextVectorization)
   - 输出: 32维 Embedding

任务:
   - tfrs.tasks.Retrieval: 优化两个塔的输出向量在同一空间中的相似度

输出:
   - saved_user_model/: 可用于 Vertex AI Prediction 的 SavedModel
   - strategy_embeddings.json: 包含所有策略向量的 JSON 文件，用于 Vector Search Index
"""

import os
import json
import logging
import numpy as np

# 强制使用 Legacy Keras (Keras 2) 以兼容 TensorFlow Recommenders
os.environ["TF_USE_LEGACY_KERAS"] = "1"

import tensorflow as tf
import tensorflow_recommenders as tfrs
import pandas as pd
from typing import Dict, Text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# 配置
# ==============================================================================
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
STRATEGIES_FILE = os.path.join(DATA_DIR, "strategies.csv")
INTERACTIONS_FILE = os.path.join(DATA_DIR, "user_interactions.csv")

EMBEDDING_DIM = 32
EPOCHS = 5
BATCH_SIZE = 128


# ==============================================================================
# 模型定义
# ==============================================================================

class UserModel(tf.keras.Model):
    """User Tower: 处理用户信息"""
    
    def __init__(self, user_ids, unique_user_ids):
        super().__init__()
        
        # User ID Embedding
        self.user_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(
                vocabulary=unique_user_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_user_ids) + 1, 32)
        ])
        
        # Risk Score (numerical) -> Dense
        self.risk_dense = tf.keras.Sequential([
            tf.keras.layers.Dense(32, activation="relu")
        ])
        
        # 融合层
        self.output_dense = tf.keras.layers.Dense(EMBEDDING_DIM)

    def call(self, inputs):
        # inputs: {"user_id": ..., "user_risk_score": ...}
        user_vector = self.user_embedding(inputs["user_id"])
        
        # 确保 risk_score 维度正确 (batch_size, 1)
        risk_score = tf.reshape(inputs["user_risk_score"], [-1, 1])
        risk_vector = self.risk_dense(risk_score)
        
        # Concatenate & Project
        return self.output_dense(tf.concat([user_vector, risk_vector], axis=1))


class StrategyModel(tf.keras.Model):
    """Strategy Tower: 处理策略信息"""
    
    def __init__(self, unique_strategy_ids, descriptions):
        super().__init__()
        
        # Strategy ID Embedding
        self.strategy_embedding = tf.keras.Sequential([
            tf.keras.layers.StringLookup(
                vocabulary=unique_strategy_ids, mask_token=None),
            tf.keras.layers.Embedding(len(unique_strategy_ids) + 1, 32)
        ])
        
        # Description Text Embedding
        self.description_vectorizer = tf.keras.layers.TextVectorization(
            max_tokens=1000, output_mode="int", output_sequence_length=20)
        self.description_vectorizer.adapt(descriptions)
        
        self.description_embedding = tf.keras.Sequential([
            self.description_vectorizer,
            tf.keras.layers.Embedding(1001, 16, mask_zero=True),
            tf.keras.layers.GlobalAveragePooling1D()
        ])
        
        # Fusion
        self.output_dense = tf.keras.layers.Dense(EMBEDDING_DIM)

    def call(self, inputs):
        # inputs: {"strategy_id": ..., "description": ...}
        
        # 允许输入仅为 string (Serving 时) 或 dict (Training 时)
        if isinstance(inputs, dict):
            strategy_id = inputs["strategy_id"]
            description = inputs["description"]
        else:
            # 假设 serving 时可能只传 ID (这里为了简单，我们还是假设输入是 dict)
            # 实际 Vertex AI 调用时，会传入 dict
            strategy_id = inputs["strategy_id"]
            description = inputs["description"]
            
        id_vector = self.strategy_embedding(strategy_id)
        desc_vector = self.description_embedding(description)
        
        return self.output_dense(tf.concat([id_vector, desc_vector], axis=1))


class TwoTowerModel(tfrs.models.Model):
    """完整的 TFRS 双塔模型"""
    
    def __init__(self, user_model, strategy_model, task):
        super().__init__()
        self.user_model = user_model
        self.strategy_model = strategy_model
        self.task = task

    def compute_loss(self, features, training=False):
        # features 是一个 batch 的数据
        # 包含 user_id, user_risk_score, strategy_id, description
        
        user_embeddings = self.user_model({
            "user_id": features["user_id"],
            "user_risk_score": features["user_risk_score"]
        })
        
        strategy_embeddings = self.strategy_model({
            "strategy_id": features["strategy_id"],
            "description": features["description"]
        })

        return self.task(user_embeddings, strategy_embeddings)


# ==============================================================================
# 数据加载与预处理
# ==============================================================================

def load_data():
    """加载 CSV 数据并转换为 TF Dataset"""
    logger.info("Loading data...")
    
    # 1. 策略数据
    strategies_df = pd.read_csv(STRATEGIES_FILE)
    strategies_df["description"] = strategies_df["description"].astype(str)
    strategies = tf.data.Dataset.from_tensor_slices(dict(strategies_df))
    
    # 2. 交互数据
    interactions_df = pd.read_csv(INTERACTIONS_FILE)
    # 只保留成功的交互 (隐式反馈)
    positive_interactions = interactions_df[interactions_df["outcome"] == 1]
    
    # 合并描述信息到交互数据中 (Training 需要)
    merged_df = pd.merge(positive_interactions, strategies_df, on="strategy_id")
    
    interactions = tf.data.Dataset.from_tensor_slices({
        "user_id": merged_df["user_id"].values,
        "user_risk_score": merged_df["user_risk_score"].values.astype(np.float32),
        "strategy_id": merged_df["strategy_id"].values,
        "description": merged_df["description"].values
    })
    
    return strategies_df, interactions, strategies


def export_user_model(user_model, export_path):
    """导出 User Tower 为 SavedModel (用于在线服务)"""
    logger.info(f"Exporting User Model to {export_path}...")
    
    # 定义 serving signature
    # 注意: Vertex AI 接收 JSON, 这里定义 input signature
    @tf.function(input_signature=[{
        "user_id": tf.TensorSpec(shape=[None], dtype=tf.string, name="user_id"),
        "user_risk_score": tf.TensorSpec(shape=[None], dtype=tf.float32, name="user_risk_score")
    }])
    def serve(inputs):
        return {"embedding": user_model(inputs)}

    tf.saved_model.save(user_model, export_path, signatures={"serving_default": serve})


def export_strategy_embeddings(strategy_model, strategies_df, export_path):
    """计算所有策略的 Embedding 并保存为 JSON (用于 Vector Search Index)"""
    logger.info(f"Exporting Strategy Embeddings to {export_path}...")
    
    embeddings = []
    
    # Batch processing to avoid OOM
    batch_size = 100
    for i in range(0, len(strategies_df), batch_size):
        batch = strategies_df.iloc[i:i+batch_size]
        
        batch_inputs = {
            "strategy_id": tf.constant(batch["strategy_id"].values),
            "description": tf.constant(batch["description"].values)
        }
        
        vectors = strategy_model(batch_inputs)
        
        for j, vector in enumerate(vectors):
            strategy_id = batch.iloc[j]["strategy_id"]
            # Vertex AI Vector Search JSON format: {"id": "...", "embedding": [...]}
            embeddings.append({
                "id": strategy_id,
                "embedding": vector.numpy().tolist()
            })
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    # Save as line-delimited JSON (JSONL)
    with open(export_path, 'w') as f:
        for item in embeddings:
            f.write(json.dumps(item) + '\n')


# ==============================================================================
# 主流程
# ==============================================================================

def main():
    # 0. 准备输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. 加载数据
    strategies_df, interactions, strategies_ds = load_data()
    
    # 获取 VocabULARIES
    unique_user_ids = interactions.map(lambda x: x["user_id"]).batch(1000).as_numpy_iterator()
    unique_user_ids = np.unique(np.concatenate(list(unique_user_ids)))
    
    unique_strategy_ids = strategies_df["strategy_id"].unique()
    descriptions = strategies_df["description"].values
    
    logger.info(f"Vocab sizes: Users={len(unique_user_ids)}, Strategies={len(unique_strategy_ids)}")
    
    # 2. 构建模型组件
    user_model = UserModel(unique_user_ids, unique_user_ids)
    strategy_model = StrategyModel(unique_strategy_ids, descriptions)
    
    # Retrieval Task
    # metrics: FactorizedTopK 用于评估 (计算验证集上的 Top-K 准确率)
    # candidates: 所有策略的 dataset，用于评估时构建候选集索引
    metrics = tfrs.metrics.FactorizedTopK(
        candidates=strategies_ds.batch(128).map(lambda x: strategy_model(x))
    )
    
    task = tfrs.tasks.Retrieval(
        metrics=metrics
    )
    
    model = TwoTowerModel(user_model, strategy_model, task)
    model.compile(optimizer=tf.keras.optimizers.Adagrad(learning_rate=0.1))
    
    # 3. 训练
    logger.info("Starting training...")
    cached_train = interactions.shuffle(10000).batch(BATCH_SIZE).cache()
    model.fit(cached_train, epochs=EPOCHS)
    
    # 4. 导出
    user_model_path = os.path.join(OUTPUT_DIR, "saved_user_model")
    export_user_model(user_model, user_model_path)
    
    embeddings_path = os.path.join(OUTPUT_DIR, "strategy_embeddings.json")
    export_strategy_embeddings(strategy_model, strategies_df, embeddings_path)
    
    logger.info("Training and export complete!")


if __name__ == "__main__":
    main()
