from sqlalchemy import Column, BigInteger, String, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(TIMESTAMP, default=func.now())