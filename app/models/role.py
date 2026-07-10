from sqlalchemy import Column, SmallInteger, String, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(SmallInteger, primary_key=True)
    name = Column(String(30), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())