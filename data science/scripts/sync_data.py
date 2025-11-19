#!/usr/bin/env python3
"""
数据同步脚本
用于在本地和 Cloud Storage 之间同步数据
"""

import argparse
import os
import sys
from google.cloud import storage
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Cloud Storage 配置
BUCKET_NAME = os.getenv("STORAGE_BUCKET_NAME", "data-science-44398.appspot.com")


def download_from_storage(bucket_name: str, remote_path: str, local_path: Path):
    """
    从 Cloud Storage 下载文件
    
    Args:
        bucket_name: 存储桶名称
        remote_path: 远程路径前缀
        local_path: 本地保存路径
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    # 列出所有文件
    blobs = bucket.list_blobs(prefix=remote_path)
    
    downloaded_count = 0
    for blob in blobs:
        # 跳过目录
        if blob.name.endswith('/'):
            continue
        
        # 构建本地文件路径
        relative_path = blob.name[len(remote_path):].lstrip('/')
        local_file = local_path / relative_path
        
        # 创建目录
        local_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 下载文件
        print(f"Downloading: {blob.name} -> {local_file}")
        blob.download_to_filename(str(local_file))
        downloaded_count += 1
    
    print(f"\n✅ Downloaded {downloaded_count} files from gs://{bucket_name}/{remote_path}")


def upload_to_storage(bucket_name: str, local_path: Path, remote_path: str):
    """
    上传文件到 Cloud Storage
    
    Args:
        bucket_name: 存储桶名称
        local_path: 本地文件路径
        remote_path: 远程路径前缀
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    
    uploaded_count = 0
    
    # 遍历本地文件
    for local_file in local_path.rglob('*'):
        # 跳过目录和隐藏文件
        if local_file.is_dir() or local_file.name.startswith('.'):
            continue
        
        # 构建远程路径
        relative_path = local_file.relative_to(local_path)
        remote_file = f"{remote_path}/{relative_path}".replace('\\', '/')
        
        # 上传文件
        print(f"Uploading: {local_file} -> gs://{bucket_name}/{remote_file}")
        blob = bucket.blob(remote_file)
        blob.upload_from_filename(str(local_file))
        uploaded_count += 1
    
    print(f"\n✅ Uploaded {uploaded_count} files to gs://{bucket_name}/{remote_path}")


def main():
    parser = argparse.ArgumentParser(description="同步本地和 Cloud Storage 的数据")
    
    parser.add_argument(
        '--download',
        action='store_true',
        help='从 Cloud Storage 下载数据到本地'
    )
    
    parser.add_argument(
        '--upload',
        action='store_true',
        help='上传本地数据到 Cloud Storage'
    )
    
    parser.add_argument(
        '--path',
        choices=['raw', 'processed', 'models', 'results', 'all'],
        default='all',
        help='指定要同步的数据类型'
    )
    
    parser.add_argument(
        '--bucket',
        default=BUCKET_NAME,
        help=f'Cloud Storage 存储桶名称 (默认: {BUCKET_NAME})'
    )
    
    args = parser.parse_args()
    
    if not args.download and not args.upload:
        print("❌ 请指定 --download 或 --upload")
        sys.exit(1)
    
    # 确定要同步的路径
    if args.path == 'all':
        paths = ['raw', 'processed', 'models', 'results']
    else:
        paths = [args.path]
    
    try:
        for path_name in paths:
            local_path = DATA_DIR / path_name
            remote_path = f"data/{path_name}"
            
            print(f"\n{'='*60}")
            print(f"同步: {path_name}")
            print(f"{'='*60}")
            
            if args.download:
                download_from_storage(args.bucket, remote_path, local_path)
            
            if args.upload:
                if not local_path.exists() or not any(local_path.iterdir()):
                    print(f"⚠️  跳过空目录: {local_path}")
                    continue
                upload_to_storage(args.bucket, local_path, remote_path)
        
        print(f"\n{'='*60}")
        print("✅ 同步完成!")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ 同步失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
