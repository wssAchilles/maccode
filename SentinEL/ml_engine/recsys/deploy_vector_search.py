"""
SentinEL Vector Search 部署脚本

负责将训练生成的策略向量 (strategy_embeddings.json) 部署到 Vertex AI Vector Search (Matching Engine)。

流程:
1. 创建/获取 MatchingEngineIndex (使用 Tree-AH 算法)
2. 创建/获取 MatchingEngineIndexEndpoint
3. 将 Index 部署到 Endpoint

前提:
1. 已运行 train_two_tower.py 并生成 output/strategy_embeddings.json
2. 策略向量文件已上传到 GCS Bucket

使用方法:
    python -m ml_engine.recsys.deploy_vector_search \
        --project sentinel-ai-project-482208 \
        --region asia-east1 \
        --gcs_bucket gs://sentinel-mlops-artifacts-sentinel-ai-project-482208 \
        --index_display_name sentinel-strategy-index
"""

import argparse
import logging
import time
import os
import json
from typing import Dict, Any, Optional

from google.cloud import aiplatform
from google.cloud import storage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==============================================================================
# 默认配置
# ==============================================================================
DEFAULT_PROJECT = "sentinel-ai-project-482208"
DEFAULT_REGION = "us-central1"  # 与 GCS Bucket 区域保持一致
DEFAULT_BUCKET = "sentinel-mlops-artifacts-sentinel-ai-project-482208"
DEFAULT_INDEX_NAME = "sentinel-strategy-index"

# 本地 embedding 文件路径 (相对于项目根目录)
LOCAL_EMBEDDING_FILE = "ml_engine/recsys/output/strategy_embeddings.json"


def upload_embeddings_to_gcs(
    project_id: str,
    bucket_name: str,
    local_path: str,
    gcs_prefix: str = "recsys/indexes"
) -> str:
    """
    上传 embeddings 文件到 GCS
    
    Args:
        project_id: GCP 项目 ID
        bucket_name: Bucket 名称
        local_path: 本地文件路径
        gcs_prefix: GCS 路径前缀
        
    Returns:
        str: GCS URI (gs://bucket/path)
    """
    logger.info(f"Uploading embeddings to GCS: {local_path} -> gs://{bucket_name}/{gcs_prefix}")
    
    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    
    filename = os.path.basename(local_path)
    blob_path = f"{gcs_prefix}/{filename}"
    blob = bucket.blob(blob_path)
    
    blob.upload_from_filename(local_path)
    
    gcs_uri = f"gs://{bucket_name}/{gcs_prefix}" # Vector Search requires directory URI
    logger.info(f"Upload complete. GCS Directory URI: {gcs_uri}")
    
    return gcs_uri


def create_index(
    display_name: str,
    gcs_source_uri: str,
    dimensions: int = 32
) -> aiplatform.MatchingEngineIndex:
    """
    创建 MatchingEngineIndex
    
    Args:
        display_name: Index 显示名称
        gcs_source_uri: GCS 目录 URI (包含 json 文件)
        dimensions: 向量维度
        
    Returns:
        MatchingEngineIndex: 创建的 Index 对象
    """
    logger.info(f"Checking for existing index: {display_name}")
    
    # 检查是否存在同名 Index
    existing_indexes = aiplatform.MatchingEngineIndex.list(
        filter=f'display_name="{display_name}"'
    )
    
    if existing_indexes:
        logger.info(f"Index already exists: {existing_indexes[0].resource_name}")
        # 注意: 实际生产中可能需要更新 Index，这里简化为复用或需手动删除重建
        return existing_indexes[0]
    
    logger.info(f"Creating new MatchingEngineIndex: {display_name}")
    
    # Tree-AH 配置已内置于 create_tree_ah_index 方法中
    # 但必须提供 approximate_neighbors_count 参数
    
    try:
        index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=display_name,
            contents_delta_uri=gcs_source_uri,
            dimensions=dimensions,
            approximate_neighbors_count=150,  # 必需参数: 近似搜索返回的邻居数
            leaf_node_embedding_count=500,    # 每个叶节点的向量数 (默认1000)
            leaf_nodes_to_search_percent=7,   # 搜索的叶节点百分比 (1-100)
            distance_measure_type="DOT_PRODUCT_DISTANCE",  # 点积相似度
            description="SentinEL Retention Strategy Index",
            sync=True  # 同步等待创建完成 (约 10-30 分钟)
        )
        logger.info(f"Index created successfully: {index.resource_name}")
        return index
        
    except Exception as e:
        logger.error(f"Failed to create index: {e}")
        raise


def create_index_endpoint(
    display_name: str,
    public_endpoint_enabled: bool = True
) -> aiplatform.MatchingEngineIndexEndpoint:
    """
    创建 Index Endpoint
    
    Args:
        display_name: Endpoint 名称
        public_endpoint_enabled: 是否启用公网访问 (便于开发测试)
        
    Returns:
        MatchingEngineIndexEndpoint: Endpoint 对象
    """
    logger.info(f"Checking for existing index endpoint: {display_name}")
    
    existing_endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
        filter=f'display_name="{display_name}"'
    )
    
    if existing_endpoints:
        logger.info(f"Endpoint already exists: {existing_endpoints[0].resource_name}")
        return existing_endpoints[0]
    
    logger.info(f"Creating new Index Endpoint: {display_name}")
    
    endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=display_name,
        public_endpoint_enabled=public_endpoint_enabled,
        description="Endpoint for SentinEL Strategy Recommendations",
        sync=True
    )
    
    logger.info(f"Endpoint created: {endpoint.resource_name}")
    return endpoint


def deploy_index(
    index: aiplatform.MatchingEngineIndex,
    endpoint: aiplatform.MatchingEngineIndexEndpoint,
    deployed_index_id: str = "sentinel_strategy_deploy_v1"
):
    """
    将 Index 部署到 Endpoint
    """
    logger.info(f"Deploying index {index.display_name} to endpoint {endpoint.display_name}...")
    
    # 检查是否已部署
    for deployed in endpoint.deployed_indexes:
        if deployed.index == index.resource_name:
            logger.info(f"Index already deployed with ID: {deployed.id}")
            return
            
    try:
        endpoint.deploy_index(
            index=index,
            deployed_index_id=deployed_index_id,
            display_name="sentinel_strategy_deploy_v1",
            machine_type="e2-standard-16",  # SHARD_SIZE_MEDIUM 需要 e2-standard-16 或更大
            min_replica_count=1,
            max_replica_count=1,
            sync=True    # 部署通常需要 10-20 分钟
        )
        logger.info("Index deployment complete!")
        
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="SentinEL Vector Search 部署")
    
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT)
    parser.add_argument("--region", type=str, default=DEFAULT_REGION)
    parser.add_argument("--gcs_bucket", type=str, default=DEFAULT_BUCKET)
    parser.add_argument("--index_display_name", type=str, default=DEFAULT_INDEX_NAME)
    
    args = parser.parse_args()
    
    # 初始化 AI Platform
    aiplatform.init(project=args.project, location=args.region)
    
    # 1. 上传 Embeddings
    if not os.path.exists(LOCAL_EMBEDDING_FILE):
        logger.error(f"Embedding file not found: {LOCAL_EMBEDDING_FILE}")
        logger.error("Please run ml_engine.recsys.train_two_tower first.")
        return
        
    gcs_uri = upload_embeddings_to_gcs(
        project_id=args.project,
        bucket_name=args.gcs_bucket,
        local_path=LOCAL_EMBEDDING_FILE
    )
    
    # 2. 创建 Index
    index = create_index(
        display_name=args.index_display_name,
        gcs_source_uri=gcs_uri,
        dimensions=32 # 与模型输出维度一致
    )
    
    # 3. 创建 Endpoint
    endpoint = create_index_endpoint(
        display_name=f"{args.index_display_name}-endpoint"
    )
    
    # 4. 部署 Index
    deploy_index(index, endpoint)
    
    # 5. 输出关键信息供后端使用
    logger.info("\n" + "="*50)
    logger.info(f"DEPLOYMENT SUCCESSFUL")
    logger.info("="*50)
    logger.info(f"Index Resource Name: {index.resource_name}")
    logger.info(f"Endpoint Resource Name: {endpoint.resource_name}")
    logger.info(f"Public Endpoint Domain: {endpoint.public_endpoint_domain_name}")
    logger.info("="*50)
    logger.info("User Tower (SavedModel) should be deployed separately to a Prediction Endpoint.")


if __name__ == "__main__":
    main()
