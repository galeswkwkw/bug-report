import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # JWT
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS"))
    
    # MinIO
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
    MINIO_BUCKET = os.getenv("MINIO_BUCKET")
    MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL")
    
    # Upload
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE"))
    MAX_RESULT_FILES = int(os.getenv("MAX_RESULT_FILES", "4"))
    
    ALLOWED_DOCUMENT_TYPES = [x.strip() for x in os.getenv("ALLOWED_DOCUMENT_TYPES").split(",")]
    ALLOWED_EVIDENCE_EXTENSIONS = [x.strip() for x in os.getenv("ALLOWED_EVIDENCE_EXTENSIONS").split(",")]
    ALLOWED_RESULT_EXTENSIONS = [x.strip() for x in os.getenv("ALLOWED_RESULT_EXTENSIONS").split(",")]
    MAX_EVIDENCE_FILE_SIZE = int(os.getenv("MAX_EVIDENCE_FILE_SIZE"))

    # SMTP
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
    SMTP_TLS = os.getenv("SMTP_TLS", "True").lower() == "true"
    
    # CORS
    ALLOWED_ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS").split(",")]