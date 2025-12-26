"""
SentinEL 序列数据提取脚本
从 BigQuery 事件表提取用户行为序列，用于训练 LSTM 时序预测模型

功能:
    1. 连接 BigQuery，提取每个用户最近 N 个事件
    2. 将事件名称映射为整数 Token ID
    3. 对序列进行 Padding/Truncating 统一长度
    4. 导出为 CSV / JSONL 格式供训练使用

使用方法:
    python extract_sequences.py \
        --project sentinel-ai-project-482208 \
        --dataset retail_ai \
        --events_table user_events \
        --output_path gs://sentinel-mlops-artifacts/training_data/sequences.csv \
        --seq_length 20

依赖:
    pip install google-cloud-bigquery pandas pyarrow
"""

import argparse
import json
import logging
from typing import Dict, List, Tuple
from pathlib import Path
from collections import defaultdict

from google.cloud import bigquery
import pandas as pd

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ==============================================================================
# 事件词汇表（Event Vocabulary）
# ==============================================================================
# 预定义的事件映射表，将事件名称映射到整数 Token ID
# 0 保留给 PAD，1 保留给 UNK（未知事件）
EVENT_VOCAB: Dict[str, int] = {
    "<PAD>": 0,
    "<UNK>": 1,
    "page_view": 2,
    "view_item": 3,
    "add_to_cart": 4,
    "remove_from_cart": 5,
    "begin_checkout": 6,
    "add_payment_info": 7,
    "purchase": 8,
    "view_promotion": 9,
    "select_promotion": 10,
    "check_policy": 11,        # 查看退货/退款政策（高流失信号）
    "view_returns": 12,        # 查看退货页面
    "contact_support": 13,     # 联系客服
    "rage_click": 14,          # 愤怒点击（连续快速点击）
    "session_start": 15,
    "session_end": 16,
    "scroll_to_bottom": 17,
    "form_abandon": 18,        # 表单放弃
    "coupon_apply": 19,
    "coupon_fail": 20,
    "wishlist_add": 21,
    "wishlist_remove": 22,
    "search": 23,
    "filter_apply": 24,
    "compare_items": 25,
    "share_item": 26,
    "review_read": 27,
    "review_write": 28,
}

# 反向映射：ID -> 事件名
ID_TO_EVENT = {v: k for k, v in EVENT_VOCAB.items()}

# 词汇表大小
VOCAB_SIZE = max(EVENT_VOCAB.values()) + 1


def get_event_id(event_name: str) -> int:
    """
    将事件名称转换为 Token ID
    
    Args:
        event_name: 原始事件名称（如 'page_view'）
        
    Returns:
        int: 对应的 Token ID，未知事件返回 1 (UNK)
    """
    return EVENT_VOCAB.get(event_name.lower().strip(), EVENT_VOCAB["<UNK>"])


def pad_sequence(sequence: List[int], max_length: int, pad_value: int = 0) -> List[int]:
    """
    对序列进行 Padding/Truncating
    
    Args:
        sequence: 原始事件 ID 序列
        max_length: 目标序列长度
        pad_value: 填充值，默认 0 (PAD token)
        
    Returns:
        List[int]: 填充/截断后的序列
    """
    if len(sequence) >= max_length:
        # 截断：保留最近的 max_length 个事件
        return sequence[-max_length:]
    else:
        # 填充：在序列前端填充 PAD
        padding = [pad_value] * (max_length - len(sequence))
        return padding + sequence


class SequenceExtractor:
    """
    用户行为序列提取器
    
    负责从 BigQuery 提取事件数据并转换为训练格式
    """
    
    def __init__(
        self,
        project_id: str,
        dataset_id: str,
        events_table: str,
        labels_table: str = "user_churn_labels",
        seq_length: int = 20
    ):
        """
        初始化提取器
        
        Args:
            project_id: GCP 项目 ID
            dataset_id: BigQuery 数据集 ID
            events_table: 事件表名
            labels_table: 流失标签表名（包含 user_id, churn_label 列）
            seq_length: 目标序列长度
        """
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.events_table = events_table
        self.labels_table = labels_table
        self.seq_length = seq_length
        
        self.client = bigquery.Client(project=project_id)
        logger.info(f"SequenceExtractor 初始化完成 | 项目: {project_id}, 序列长度: {seq_length}")
    
    def extract_sequences(self, limit: int = None) -> pd.DataFrame:
        """
        从 BigQuery 提取用户行为序列
        
        SQL 逻辑:
            1. 获取每个用户的最近 N 个事件（按时间倒序）
            2. 聚合为数组
            3. JOIN 流失标签表获取 label
        
        Args:
            limit: 可选，限制提取的用户数量（用于测试）
            
        Returns:
            pd.DataFrame: 包含 user_id, event_sequence, label 的 DataFrame
        """
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
        WITH user_events AS (
            SELECT
                user_id,
                event_name,
                event_timestamp,
                ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_timestamp DESC) as event_rank
            FROM
                `{self.project_id}.{self.dataset_id}.{self.events_table}`
            WHERE
                event_name IS NOT NULL
        ),
        recent_sequences AS (
            SELECT
                user_id,
                ARRAY_AGG(event_name ORDER BY event_timestamp ASC) AS event_sequence
            FROM
                user_events
            WHERE
                event_rank <= {self.seq_length}
            GROUP BY
                user_id
        )
        SELECT
            s.user_id,
            s.event_sequence,
            COALESCE(l.churn_label, 0) AS label
        FROM
            recent_sequences s
        LEFT JOIN
            `{self.project_id}.{self.dataset_id}.{self.labels_table}` l
        ON
            s.user_id = l.user_id
        {limit_clause}
        """
        
        logger.info("开始执行 BigQuery 查询...")
        query_job = self.client.query(query)
        results = query_job.result()
        
        # 转换为 DataFrame
        data = []
        for row in results:
            # 将事件名称转换为 Token IDs
            event_ids = [get_event_id(e) for e in row.event_sequence]
            # Pad/Truncate
            padded_ids = pad_sequence(event_ids, self.seq_length)
            
            data.append({
                "user_id": str(row.user_id),
                "event_sequence": json.dumps(padded_ids),  # JSON 字符串存储
                "label": int(row.label)
            })
        
        df = pd.DataFrame(data)
        logger.info(f"提取完成 | 用户数: {len(df)}, 流失用户: {df['label'].sum()}")
        
        return df
    
    def export_to_csv(self, df: pd.DataFrame, output_path: str) -> None:
        """
        导出 DataFrame 到 CSV 文件
        
        Args:
            df: 数据 DataFrame
            output_path: 输出路径（支持 GCS gs:// 或本地路径）
        """
        logger.info(f"导出数据到: {output_path}")
        
        if output_path.startswith("gs://"):
            # GCS 路径
            df.to_csv(output_path, index=False)
        else:
            # 本地路径
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
        
        logger.info(f"导出成功 | 记录数: {len(df)}")
    
    def export_to_jsonl(self, df: pd.DataFrame, output_path: str) -> None:
        """
        导出 DataFrame 到 JSONL 文件（每行一个 JSON 对象）
        
        Args:
            df: 数据 DataFrame
            output_path: 输出路径
        """
        logger.info(f"导出数据到 JSONL: {output_path}")
        
        # 将序列字符串解析回列表
        records = []
        for _, row in df.iterrows():
            records.append({
                "user_id": row["user_id"],
                "event_sequence": json.loads(row["event_sequence"]),
                "label": row["label"]
            })
        
        if output_path.startswith("gs://"):
            # GCS 需要特殊处理
            from google.cloud import storage
            bucket_name = output_path.replace("gs://", "").split("/")[0]
            blob_name = "/".join(output_path.replace("gs://", "").split("/")[1:])
            
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            jsonl_content = "\n".join(json.dumps(r) for r in records)
            blob.upload_from_string(jsonl_content)
        else:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                for record in records:
                    f.write(json.dumps(record) + "\n")
        
        logger.info(f"JSONL 导出成功 | 记录数: {len(records)}")


def generate_synthetic_data(num_users: int = 1000, seq_length: int = 20) -> pd.DataFrame:
    """
    生成合成数据用于模型开发和测试（无需 BigQuery）
    
    流失模式特征:
        - 高概率包含: check_policy, view_returns, rage_click, contact_support
        - 低概率包含: purchase, coupon_apply
    
    Args:
        num_users: 用户数量
        seq_length: 序列长度
        
    Returns:
        pd.DataFrame: 合成的训练数据
    """
    import random
    
    logger.info(f"生成合成数据 | 用户数: {num_users}, 序列长度: {seq_length}")
    
    # 正常用户的事件分布
    normal_events = ["page_view", "view_item", "add_to_cart", "begin_checkout", 
                     "purchase", "search", "filter_apply"]
    
    # 流失用户的事件分布（包含高风险信号）
    churn_events = ["page_view", "view_item", "check_policy", "view_returns",
                    "rage_click", "contact_support", "remove_from_cart", "form_abandon"]
    
    data = []
    churn_count = 0
    
    for user_id in range(num_users):
        # 30% 流失率
        is_churn = random.random() < 0.3
        
        if is_churn:
            churn_count += 1
            events = [random.choice(churn_events) for _ in range(seq_length)]
        else:
            events = [random.choice(normal_events) for _ in range(seq_length)]
        
        # 转换为 Token IDs
        event_ids = [get_event_id(e) for e in events]
        
        data.append({
            "user_id": str(user_id),
            "event_sequence": json.dumps(event_ids),
            "label": 1 if is_churn else 0
        })
    
    logger.info(f"合成数据生成完成 | 流失用户: {churn_count}/{num_users}")
    return pd.DataFrame(data)


def main():
    parser = argparse.ArgumentParser(description="SentinEL 序列数据提取工具")
    parser.add_argument("--project", type=str, default="sentinel-ai-project-482208",
                        help="GCP 项目 ID")
    parser.add_argument("--dataset", type=str, default="retail_ai",
                        help="BigQuery 数据集 ID")
    parser.add_argument("--events_table", type=str, default="user_events",
                        help="事件表名")
    parser.add_argument("--labels_table", type=str, default="user_churn_labels",
                        help="流失标签表名")
    parser.add_argument("--output_path", type=str, required=True,
                        help="输出路径 (CSV 或 JSONL)")
    parser.add_argument("--seq_length", type=int, default=20,
                        help="目标序列长度")
    parser.add_argument("--limit", type=int, default=None,
                        help="限制提取用户数量（测试用）")
    parser.add_argument("--synthetic", action="store_true",
                        help="使用合成数据（无需 BigQuery）")
    parser.add_argument("--num_synthetic_users", type=int, default=5000,
                        help="合成用户数量")
    
    args = parser.parse_args()
    
    if args.synthetic:
        # 生成合成数据
        df = generate_synthetic_data(args.num_synthetic_users, args.seq_length)
    else:
        # 从 BigQuery 提取
        extractor = SequenceExtractor(
            project_id=args.project,
            dataset_id=args.dataset,
            events_table=args.events_table,
            labels_table=args.labels_table,
            seq_length=args.seq_length
        )
        df = extractor.extract_sequences(limit=args.limit)
    
    # 导出
    if args.output_path.endswith(".jsonl"):
        if args.synthetic:
            # 直接导出
            SequenceExtractor(args.project, args.dataset, args.events_table, 
                              args.labels_table, args.seq_length).export_to_jsonl(df, args.output_path)
        else:
            extractor.export_to_jsonl(df, args.output_path)
    else:
        df.to_csv(args.output_path, index=False)
        logger.info(f"CSV 导出完成: {args.output_path}")
    
    # 打印词汇表信息
    logger.info(f"事件词汇表大小: {VOCAB_SIZE}")
    logger.info(f"词汇表: {list(EVENT_VOCAB.keys())[:10]}...")


if __name__ == "__main__":
    main()
