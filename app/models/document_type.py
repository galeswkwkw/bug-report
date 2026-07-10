from sqlalchemy import Column, SmallInteger, String, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class DocumentType(Base):
    __tablename__ = "document_types"
    
    id = Column(SmallInteger, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    required = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())