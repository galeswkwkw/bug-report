from sqlalchemy import Column, BigInteger, String, Text, Boolean, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100), nullable=False)
    domain = Column(String(255), nullable=False, unique=True)
    asset_type = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())