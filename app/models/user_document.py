from sqlalchemy import Column, BigInteger, SmallInteger, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class UserDocument(Base):
    __tablename__ = "user_documents"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_type_id = Column(SmallInteger, ForeignKey("document_types.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    object_name = Column(String(255), nullable=False)
    bucket_name = Column(String(100), default="documents")
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="documents")
    document_type = relationship("DocumentType")