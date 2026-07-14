from sqlalchemy import Column, BigInteger, String, Text, Integer, TIMESTAMP, ForeignKey, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    asset_id = Column(BigInteger, ForeignKey("assets.id"), nullable=False)
    reviewer_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    assigned_to = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    steps_to_reproduce = Column(Text, nullable=False)
    steps_to_resolve = Column(Text, nullable=True)
    impact = Column(Text, nullable=True)
    
    severity = Column(String(20), nullable=False)
    point = Column(Integer, default=0)
    
    status = Column(String(20), default="Submitted")
    review_comment = Column(Text, nullable=True)
    reject_reason = Column(Text, nullable=True)
    reviewed_at = Column(TIMESTAMP, nullable=True)
    
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    asset = relationship("Asset")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    evidences = relationship("ReportEvidence", back_populates="report", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("severity IN ('Critical', 'High', 'Medium', 'Low', 'Informational')"),
        CheckConstraint("status IN ('Submitted', 'Accepted', 'Rejected')"),
    )