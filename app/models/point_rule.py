from sqlalchemy import Column, SmallInteger, String, Integer, TIMESTAMP
from sqlalchemy.sql import func
from app.database import Base

class PointRule(Base):
    __tablename__ = "point_rules"
    
    id = Column(SmallInteger, primary_key=True)
    severity = Column(String(20), nullable=False, unique=True)
    point = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())