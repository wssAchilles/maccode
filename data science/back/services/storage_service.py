"""
Google Cloud Storage 服务
用于上传、下载和管理文件
"""

from google.cloud import storage
from google.oauth2 import service_account
import os
import pandas as pd
import tempfile
from datetime import datetime, timedelta
from urllib.parse import unquote
from config import Config
from typing import Dict, Optional


class StorageService:
    """Cloud Storage 服务类"""
    
    def __init__(self, bucket_name=None):
        """
        初始化 Storage 服务
        
        Args:
            bucket_name: 存储桶名称
        """
        self.project_id = os.getenv('GCP_PROJECT_ID') or Config.GCP_PROJECT_ID
        self.credentials = self._load_credentials()
        if self.credentials:
            self.client = storage.Client(project=self.project_id, credentials=self.credentials)
        else:
            if not self._is_running_in_gae():
                raise EnvironmentError(
                    "未检测到本地 GCP 凭证。请设置 GOOGLE_APPLICATION_CREDENTIALS 或 GCP_SERVICE_ACCOUNT_JSON 环境变量。"
                )
            self.client = storage.Client(project=self.project_id)

        self.bucket_name = bucket_name or os.getenv('STORAGE_BUCKET_NAME') or Config.STORAGE_BUCKET_NAME
        self.bucket = self.client.bucket(self.bucket_name)

    def _load_credentials(self):
        """在本地环境加载显式服务账号凭证"""
        # 优先使用 JSON 字符串 (CI/CD 或密钥管理服务常用)
        service_account_json = os.getenv('GCP_SERVICE_ACCOUNT_JSON')
        if service_account_json:
            try:
                import json
                info = json.loads(service_account_json)
                creds = service_account.Credentials.from_service_account_info(info)
                print("✅ 已通过 GCP_SERVICE_ACCOUNT_JSON 加载凭证")
                return creds
            except Exception as e:
                print(f"❌ 解析 GCP_SERVICE_ACCOUNT_JSON 失败: {e}")
                return None

        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            return None

        if not os.path.exists(credentials_path):
            print(f"⚠️  指定的 GOOGLE_APPLICATION_CREDENTIALS 路径不存在: {credentials_path}")
            return None

        try:
            creds = service_account.Credentials.from_service_account_file(credentials_path)
            print("✅ 已通过 GOOGLE_APPLICATION_CREDENTIALS 加载凭证")
            return creds
        except Exception as e:
            print(f"❌ 加载本地凭证失败: {e}")
            return None

    @staticmethod
    def _is_running_in_gae() -> bool:
        return bool(os.getenv('GAE_ENV') or os.getenv('K_SERVICE'))
    
    def upload_file(self, file_data, destination_path, content_type=None):
        """
        上传文件到 Cloud Storage
        
        Args:
            file_data: 文件数据 (bytes 或 file-like object)
            destination_path: 目标路径 (例如: 'uploads/file.csv')
            content_type: 文件类型 (例如: 'text/csv')
            
        Returns:
            str: 文件的公开 URL
        """
        blob = self.bucket.blob(destination_path)
        
        if content_type:
            blob.content_type = content_type
        
        # 上传文件
        if isinstance(file_data, bytes):
            blob.upload_from_string(file_data, content_type=content_type)
        else:
            blob.upload_from_file(file_data, content_type=content_type)
        
        return f"gs://{self.bucket_name}/{destination_path}"

    def _normalize_blob_path(self, file_path: str) -> str:
        if not file_path:
            return file_path
        normalized = str(file_path).strip()
        if normalized.startswith('gs://'):
            without_scheme = normalized[len('gs://'):]
            bucket_name, _, blob_name = without_scheme.partition('/')
            if blob_name:
                return blob_name
            return ''

        download_marker = '/o/'
        if download_marker in normalized and 'storage.googleapis.com' in normalized:
            encoded_blob = normalized.split(download_marker, 1)[1].split('?', 1)[0]
            return unquote(encoded_blob)

        return normalized.lstrip('/')
    
    def download_file(self, source_path):
        """
        从 Cloud Storage 下载文件
        
        Args:
            source_path: 文件路径
            
        Returns:
            bytes: 文件内容
        """
        blob = self.bucket.blob(self._normalize_blob_path(source_path))
        return blob.download_as_bytes()
    
    def delete_file(self, file_path):
        """
        删除文件
        
        Args:
            file_path: 文件路径
        """
        blob = self.bucket.blob(self._normalize_blob_path(file_path))
        blob.delete()
    
    def list_files(self, prefix=None):
        """
        列出文件
        
        Args:
            prefix: 路径前缀 (可选)
            
        Returns:
            list: 文件列表
        """
        normalized_prefix = None if prefix is None else self._normalize_blob_path(prefix)
        blobs = self.bucket.list_blobs(prefix=normalized_prefix)
        return [blob.name for blob in blobs]
    
    def get_signed_url(self, file_path, expiration_minutes=60):
        """
        生成签名 URL (临时访问链接)
        
        Args:
            file_path: 文件路径
            expiration_minutes: 过期时间(分钟)
            
        Returns:
            str: 签名 URL
        """
        blob = self.bucket.blob(self._normalize_blob_path(file_path))
        url = blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method='GET'
        )
        return url

    def generate_upload_signed_url(self, destination_path, content_type, expiration_minutes=15):
        """
        生成上传用的签名 URL (PUT 请求)
        使用 Impersonated Credentials 签名，适用于 GAE 环境
        
        Args:
            destination_path: 目标路径
            content_type: 文件类型
            expiration_minutes: 过期时间(分钟)
            
        Returns:
            str: 签名 URL
        """
        from google.auth import default, impersonated_credentials
        from google.cloud import storage
        
        # 获取默认凭据和项目 ID
        credentials, project = default()
        
        # 获取服务账号邮箱
        service_account_email = f"{project}@appspot.gserviceaccount.com"
        
        try:
            # 创建 Impersonated Credentials
            # 这会让当前凭据(默认服务账号)去扮演它自己，从而获取签名能力
            # 需要启用 IAM Service Account Credentials API
            target_credentials = impersonated_credentials.Credentials(
                source_credentials=credentials,
                target_principal=service_account_email,
                target_scopes=['https://www.googleapis.com/auth/cloud-platform'],
                lifetime=timedelta(minutes=expiration_minutes + 5)
            )
            
            # 使用 Impersonated Credentials 创建临时的 Storage Client
            # 这样生成的 blob 会自动使用 IAM API 进行签名
            temp_client = storage.Client(credentials=target_credentials, project=project)
            temp_bucket = temp_client.bucket(self.bucket_name)
            blob = temp_bucket.blob(destination_path)
            
            url = blob.generate_signed_url(
                expiration=timedelta(minutes=expiration_minutes),
                method='PUT',
                content_type=content_type,
                version='v4'
            )
            return url
        except Exception as e:
            print(f"Signed URL generation error: {e}")
            # 如果 IAM 签名失败，尝试回退到默认方法（本地开发环境可能需要）
            try:
                blob = self.bucket.blob(destination_path)
                return blob.generate_signed_url(
                    expiration=timedelta(minutes=expiration_minutes),
                    method='PUT',
                    content_type=content_type,
                    version='v4'
                )
            except Exception as fallback_error:
                print(f"Fallback generation error: {fallback_error}")
                raise e
    
    def file_exists(self, file_path):
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 文件是否存在
        """
        blob = self.bucket.blob(self._normalize_blob_path(file_path))
        return blob.exists()

    def get_file_metadata(self, file_path: str) -> Dict[str, Optional[object]]:
        """读取对象元数据，供预算护栏和路由层使用。"""
        normalized_path = self._normalize_blob_path(file_path)
        blob = self.bucket.blob(normalized_path)
        if not blob.exists():
            return {
                'exists': False,
                'size': None,
                'updated': None,
                'content_type': None,
                'bucket': self.bucket_name,
                'path': normalized_path,
            }
        blob.reload()
        return {
            'exists': True,
            'size': blob.size,
            'updated': blob.updated,
            'content_type': blob.content_type,
            'bucket': self.bucket_name,
            'path': blob.name,
        }
    
    def append_and_trim_csv(
        self, 
        file_path: str, 
        new_row_dict: Dict, 
        max_rows: int = 5000
    ) -> bool:
        """
        智能 CSV 管理: 追加新行并保持滑动窗口
        
        此方法专为 GAE F1 环境设计，使用 /tmp 目录处理文件，
        避免内存溢出。实现增量数据追加和自动修剪旧数据。
        
        Args:
            file_path: Firebase Storage 中的 CSV 文件路径 (例如: 'data/processed/cleaned_energy_data_all.csv')
            new_row_dict: 要追加的新行数据 (字典格式)
            max_rows: 最大保留行数，超过则删除最旧的数据 (默认 5000 行约 7 个月)
            
        Returns:
            bool: 操作是否成功
            
        Raises:
            Exception: 文件操作失败时抛出异常
            
        Example:
            >>> storage = StorageService()
            >>> new_data = {
            ...     'Date': '2024-11-24 08:00:00',
            ...     'Hour': 8,
            ...     'DayOfWeek': 6,
            ...     'Temperature': 25.5,
            ...     'Price': 0.6,
            ...     'Site_Load': 1250.0
            ... }
            >>> storage.append_and_trim_csv('data/processed/cleaned_energy_data_all.csv', new_data)
        """
        temp_file_path = None
        
        try:
            print(f"📝 开始 CSV 追加操作: {file_path}")
            
            # 使用 /tmp 目录 (GAE 唯一可写目录)
            temp_file_path = os.path.join(tempfile.gettempdir(), f'temp_csv_{os.getpid()}.csv')
            
            # 1. 检查文件是否存在
            blob = self.bucket.blob(file_path)
            file_exists = blob.exists()
            
            if file_exists:
                print(f"   ✓ 文件存在，下载到: {temp_file_path}")
                
                # 2. 下载现有文件到 /tmp
                blob.download_to_filename(temp_file_path)
                
                # 3. 读取 CSV (使用 chunksize 避免大文件内存问题)
                try:
                    df = pd.read_csv(temp_file_path)
                    original_rows = len(df)
                    print(f"   ✓ 读取成功: {original_rows} 行")
                    
                    # 4. 修剪数据 (保留最新的 max_rows 行)
                    if original_rows >= max_rows:
                        df = df.iloc[-(max_rows - 1):]  # 保留最新的 max_rows-1 行，为新行留空间
                        print(f"   ✂️  修剪数据: {original_rows} → {len(df)} 行")
                    
                except pd.errors.EmptyDataError:
                    print(f"   ⚠️  文件为空，创建新 DataFrame")
                    df = pd.DataFrame()
                    
            else:
                print(f"   ℹ️  文件不存在，创建新文件")
                df = pd.DataFrame()
            
            # 5. 追加新行
            new_row_df = pd.DataFrame([new_row_dict])
            df = pd.concat([df, new_row_df], ignore_index=True)
            print(f"   ✓ 追加新行，当前总行数: {len(df)}")
            
            # 6. 保存到临时文件
            df.to_csv(temp_file_path, index=False)
            print(f"   ✓ 保存到临时文件")
            
            # 7. 上传回 Firebase Storage
            blob.upload_from_filename(temp_file_path, content_type='text/csv')
            print(f"   ✓ 上传到 Firebase Storage: gs://{self.bucket_name}/{file_path}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ CSV 追加失败: {str(e)}")
            raise Exception(f"Failed to append and trim CSV: {str(e)}")
            
        finally:
            # 8. 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print(f"   🧹 清理临时文件")
                except Exception as e:
                    print(f"   ⚠️  清理临时文件失败: {str(e)}")
    
    def download_to_temp(self, file_path: str) -> Optional[str]:
        """
        下载文件到 /tmp 目录并返回临时文件路径
        
        Args:
            file_path: Firebase Storage 中的文件路径
            
        Returns:
            str: 临时文件的绝对路径，如果失败返回 None
        """
        try:
            blob = self.bucket.blob(file_path)
            
            if not blob.exists():
                print(f"❌ 文件不存在: {file_path}")
                return None
            
            # 生成临时文件路径
            file_extension = os.path.splitext(file_path)[1]
            temp_file_path = os.path.join(
                tempfile.gettempdir(), 
                f'download_{os.getpid()}_{os.path.basename(file_path)}'
            )
            
            # 下载文件
            blob.download_to_filename(temp_file_path)
            print(f"✓ 下载文件到: {temp_file_path}")
            
            return temp_file_path
            
        except Exception as e:
            print(f"❌ 下载文件失败: {str(e)}")
            return None
