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