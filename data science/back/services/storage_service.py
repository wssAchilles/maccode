"""
Google Cloud Storage 服务
用于上传、下载和管理文件
"""

from google.cloud import storage
import os
from datetime import datetime, timedelta
from config import Config


class StorageService:
    """Cloud Storage 服务类"""
    
    def __init__(self, bucket_name=None):
        """
        初始化 Storage 服务
        
        Args:
            bucket_name: 存储桶名称
        """
        self.client = storage.Client()
        self.bucket_name = bucket_name or os.getenv('STORAGE_BUCKET_NAME') or Config.STORAGE_BUCKET_NAME
        self.bucket = self.client.bucket(self.bucket_name)
    
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
            blob.upload_from_string(file_data)
        else:
            blob.upload_from_file(file_data)
        
        return f"gs://{self.bucket_name}/{destination_path}"
    
    def download_file(self, source_path):
        """
        从 Cloud Storage 下载文件
        
        Args:
            source_path: 文件路径
            
        Returns:
            bytes: 文件内容
        """
        blob = self.bucket.blob(source_path)
        return blob.download_as_bytes()
    
    def delete_file(self, file_path):
        """
        删除文件
        
        Args:
            file_path: 文件路径
        """
        blob = self.bucket.blob(file_path)
        blob.delete()
    
    def list_files(self, prefix=None):
        """
        列出文件
        
        Args:
            prefix: 路径前缀 (可选)
            
        Returns:
            list: 文件列表
        """
        blobs = self.bucket.list_blobs(prefix=prefix)
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
        blob = self.bucket.blob(file_path)
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
        blob = self.bucket.blob(file_path)
        return blob.exists()
