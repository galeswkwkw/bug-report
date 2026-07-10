from sqlalchemy import Column, BigInteger, SmallInteger, String, Text, Integer, TIMESTAMP, CheckConstraint, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)
    role_id = Column(SmallInteger, ForeignKey("roles.id"), nullable=False)
    department_id = Column(BigInteger, ForeignKey("departments.id"), nullable=True)
    researcher_type = Column(String(20), nullable=False)
    employee_id = Column(String(30), nullable=True)
    company = Column(String(150), nullable=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    phone_number = Column(String(20), nullable=True)
    password_hash = Column(Text, nullable=False)
    total_point = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="Pending")
    
    position = Column(String(100), nullable=True)
    office_location = Column(String(200), nullable=True)
    
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        CheckConstraint("researcher_type IN ('Internal', 'External')"),
        CheckConstraint("status IN ('Pending', 'Active', 'Rejected')"),
    )
    
    # Relationships
    documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")