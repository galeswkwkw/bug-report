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
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 20))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
    
    # MinIO
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "False").lower() == "true"
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "uploads")
    MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "https://media-bugbounty.sprintasia.co.id:8443")
    
    # Upload
    UPLOAD_DIR = "uploads"
    MAX_FILE_SIZE = 250 * 1024 * 1024
    MAX_RESULT_FILES = 4 
    ALLOWED_DOCUMENT_TYPES = ["KTP", "NDA", "CV", "PORTFOLIO"]
    
    ALLOWED_EVIDENCE_EXTENSIONS = [".pdf", ".csv", ".jpg", ".png", ".mp4", ".tar.gz"]
    ALLOWED_RESULT_EXTENSIONS = [".pdf", ".csv", ".jpg", ".png", ".mp4", ".tar.gz"]
    MAX_EVIDENCE_FILE_SIZE = 100 * 1024 * 1024

    # SMTP
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_TLS = os.getenv("SMTP_TLS", "True").lower() == "true"