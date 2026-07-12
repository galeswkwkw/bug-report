from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class ReportEvidence(Base):
    __tablename__ = "report_evidences"
    
    id = Column(BigInteger, primary_key=True)
    report_id = Column(BigInteger, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False)
    
    file_name = Column(String(255), nullable=False)
    object_name = Column(String(255), nullable=False)
    bucket_name = Column(String(100), default="uploads")
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String(100), nullable=False)
    
    created_at = Column(TIMESTAMP, default=func.now())
    
    # Relationship
    report = relationship("Report") 