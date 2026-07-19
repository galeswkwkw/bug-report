from sqlalchemy import Column, BigInteger, Integer, String, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False)  
    reference_id = Column(BigInteger, nullable=True)  
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.now())
    
    
    user = relationship("User", backref="notifications")