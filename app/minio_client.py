from minio import Minio
from minio.error import S3Error
from app.config import Config
import os
from datetime import timedelta 

class MinioClient:
    def __init__(self):
        self.client = Minio(
            Config.MINIO_ENDPOINT,
            access_key=Config.MINIO_ACCESS_KEY,
            secret_key=Config.MINIO_SECRET_KEY,
            secure=Config.MINIO_SECURE
        )
        self._ensure_buckets()
    
    def _ensure_buckets(self):
        """Create buckets if they don't exist"""
        buckets = ["documents", "evidence"]
        for bucket in buckets:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
    
    def upload_file(self, bucket_name: str, object_name: str, file_content: bytes, content_type: str = None):
        """Upload file to MinIO from bytes"""
        import io
        try:
            file_size = len(file_content)
            
            result = self.client.put_object(
                bucket_name,
                object_name,
                io.BytesIO(file_content),
                file_size,
                content_type=content_type or "application/octet-stream"
            )
            
            return {
                "bucket_name": bucket_name,
                "object_name": object_name,
                "size": file_size,
                "content_type": content_type
            }
        except S3Error as e:
            raise Exception(f"MinIO upload failed: {str(e)}")
    
    def get_presigned_url(self, bucket_name: str, object_name: str, expiry: int = 3600):
        """Generate presigned URL for file access"""
        try:
            url = self.client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expiry) 
            )
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

minio_client = MinioClient()