import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # JWT
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    
    # MinIO
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uploads")  

    MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "https://media-bugbounty.sprintasia.net:8443")
    
    # Upload
    UPLOAD_DIR = "uploads"
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 10MB
    ALLOWED_DOCUMENT_TYPES = ["KTP", "NDA", "CV", "PORTFOLIO"]