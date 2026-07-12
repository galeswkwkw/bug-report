from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import SessionLocal
from app.models import User, Department, UserDocument, DocumentType, Role  
from app.schemas import ( 
    AdminActionResponse
)
from app.auth import get_current_admin
from app.minio_client import minio_client

router = APIRouter(prefix="/admin", tags=["Admin"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# GET /admin/users/rejected - GET REJECTED USERS 
@router.get("/users/rejected")
async def get_rejected_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all rejected users (status = Rejected) - Admin only
    """
    rejected_users = db.query(User).filter(User.status == "Rejected").order_by(User.created_at.desc()).all()
    
    result = []
    for user in rejected_users:
        department = db.query(Department).filter(Department.id == user.department_id).first()
        
        role = db.query(Role).filter(Role.id == user.role_id).first()
        
        result.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "researcher_type": user.researcher_type,
            "company": user.company,
            "employee_id": user.employee_id,
            "department_name": department.name if department else None,
            "role_name": role.name if role else None,
            "total_point": user.total_point,
            "status": user.status,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "rejected_at": user.updated_at  
        })
    
    return {
        "success": True,
        "count": len(result),
        "data": result
    }

# GET /admin/users/pending
@router.get("/users/pending")
async def get_pending_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all pending users for admin review
    """
    pending_users = db.query(User).filter(User.status == "Pending").all()
    
    result = []
    for user in pending_users:
        department = db.query(Department).filter(Department.id == user.department_id).first()
        documents = db.query(UserDocument).filter(UserDocument.user_id == user.id).all()
        doc_list = []
        for doc in documents:
            doc_type = db.query(DocumentType).filter(DocumentType.id == doc.document_type_id).first()
          
            url = minio_client.get_presigned_url(object_name=doc.object_name, expiry=3600)
            doc_list.append({
                "id": doc.id,
                "document_type": doc_type.name if doc_type else None,
                "file_name": doc.file_name,
                "object_name": doc.object_name,
                "file_size": doc.file_size,
                "created_at": doc.created_at,
                "url": url
            })
        
        result.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "researcher_type": user.researcher_type,
            "company": user.company,
            "employee_id": user.employee_id,
            "department_name": department.name if department else None,
            "created_at": user.created_at,
            "status": user.status,
            "documents": doc_list
        })
    
    return {
        "success": True,
        "count": len(result),
        "data": result
    }

# GET /admin/users/approved - GET APPROVED USERS (ADMIN ONLY)
@router.get("/users/approved")
async def get_approved_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all approved users (status = Active) - Admin only
    """
    approved_users = db.query(User).filter(User.status == "Active").order_by(User.created_at.desc()).all()
    
    result = []
    for user in approved_users:
        # Get department name
        department = db.query(Department).filter(Department.id == user.department_id).first()
        
        # Get role name
        role = db.query(Role).filter(Role.id == user.role_id).first()
        
        result.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "researcher_type": user.researcher_type,
            "company": user.company,
            "employee_id": user.employee_id,
            "department_name": department.name if department else None,
            "role_name": role.name if role else None,
            "total_point": user.total_point,
            "status": user.status,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        })
    
    return {
        "success": True,
        "count": len(result),
        "data": result
    }



# PUT /admin/users/{id}/approve
@router.put("/users/{user_id}/approve", response_model=AdminActionResponse)
async def approve_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Approve a pending user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.status != "Pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve user with status: {user.status}"
        )
    
    user.status = "Active"
    user.updated_at = func.now()
    db.commit()
    db.refresh(user)
    
    return AdminActionResponse(
        success=True,
        message=f"User {user.full_name} has been approved",
        user_id=user.id,
        new_status="Active"
    )

# PUT /admin/users/{id}/reject

@router.put("/users/{user_id}/reject", response_model=AdminActionResponse)
async def reject_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Reject a pending user
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.status != "Pending":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reject user with status: {user.status}"
        )
    
    user.status = "Rejected"
    user.updated_at = func.now()
    db.commit()
    db.refresh(user)
    
    return AdminActionResponse(
        success=True,
        message=f"User {user.full_name} has been rejected",
        user_id=user.id,
        new_status="Rejected"
    )