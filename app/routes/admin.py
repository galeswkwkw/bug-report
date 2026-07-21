from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional
from datetime import datetime 

from app.database import SessionLocal
from app.models import User, Department, UserDocument, DocumentType, Role, Report    
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
        


# GET /admin/users - GET ALL USERS (ADMIN ONLY)

@router.get("/users")
async def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    role: Optional[str] = None, 
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get all users with filters and pagination (Admin only).
    
    Query Parameters:
    - status: filter by status (Pending, Active, Rejected)
    - role: filter by role name (admin, security_team, researcher)
    - search: search by name or email
    - limit: number of results per page (default 50)
    - offset: number of results to skip (default 0)
    """
    
    query = db.query(User)
    
    
    if status:
        query = query.filter(User.status == status)
    
    
    if role:
        
        role_mapping = {
            "admin": 1,
            "security_team": 2,
            "researcher": 3
        }
        
        role_id = role_mapping.get(role.lower())
        if role_id:
            query = query.filter(User.role_id == role_id)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be: admin, security_team, researcher"
            )
    
    
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) | 
            (User.email.ilike(f"%{search}%"))
        )
    
    
    total_count = query.count()
    
    
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    
    result = []
    for user in users:
        role_obj = db.query(Role).filter(Role.id == user.role_id).first()
        department = db.query(Department).filter(Department.id == user.department_id).first()
        
        result.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "researcher_type": user.researcher_type,
            "employee_id": user.employee_id,
            "company": user.company,
            "position": user.position,
            "office_location": user.office_location,
            "role_id": user.role_id,
            "role_name": role_obj.name if role_obj else None,
            "department_id": user.department_id,
            "department_name": department.name if department else None,
            "total_point": user.total_point,
            "status": user.status,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        })
    
    return {
        "success": True,
        "data": result,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "next_offset": offset + limit if offset + limit < total_count else None
        }
    }

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

# GET /security-teams - GET ALL SECURITY TEAM MEMBERS (ADMIN ONLY)
@router.get("/security-teams")
async def get_security_teams(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get all Security Team members (role_id = 2) - Admin only.
    """
    security_teams = db.query(User).filter(User.role_id == 2).order_by(User.full_name).all()
    
    result = []
    for user in security_teams:
        result.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "status": user.status,
            "total_reports_assigned": db.query(Report).filter(Report.assigned_to == user.id).count(),
            "total_reports_reviewed": db.query(Report).filter(
                Report.reviewer_id == user.id,
                Report.status.in_(["Accepted", "Rejected"])
            ).count()
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
            "updated_at": user.updated_at
        })
    
    return {
        "success": True,
        "count": len(result),
        "data": result
    }
# GET /admin/users - GET ALL USERS (ADMIN ONLY)
@router.get("/users")
async def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    role_id: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get all users with filters and pagination (Admin only).
    
    Query Parameters:
    - status: filter by status (Pending, Active, Rejected)
    - role_id: filter by role_id (1=Admin, 2=Security, 3=Researcher)
    - search: search by name or email
    - limit: number of results per page (default 50)
    - offset: number of results to skip (default 0)
    """
    query = db.query(User)
    
    if status:
        query = query.filter(User.status == status)
    
    if role_id:
        query = query.filter(User.role_id == role_id)
    
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) | 
            (User.email.ilike(f"%{search}%"))
        )
    
    total_count = query.count()
    users = query.order_by(User.created_at.desc()).offset(offset).limit(limit).all()
    
    result = []
    for user in users:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        department = db.query(Department).filter(Department.id == user.department_id).first()
        
        # 🔥 AMBIL DOKUMEN USER
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
                "content_type": doc.content_type,
                "created_at": doc.created_at,
                "url": url
            })
        
        result.append({
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "researcher_type": user.researcher_type,
            "employee_id": user.employee_id,
            "company": user.company,
            "position": user.position,
            "office_location": user.office_location,
            "role_id": user.role_id,
            "role_name": role.name if role else None,
            "department_id": user.department_id,
            "department_name": department.name if department else None,
            "total_point": user.total_point,
            "status": user.status,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "documents": doc_list  # 🔥 TAMBAHKAN!
        })
    
    return {
        "success": True,
        "data": result,
        "pagination": {
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "next_offset": offset + limit if offset + limit < total_count else None
        }
    }

# POST /admin/security-teams - ADD SECURITY TEAM MEMBER (ADMIN ONLY)

@router.post("/security-teams")
async def create_security_team(
    request: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Add a new Security Team member (Admin only).
    """
    
    full_name = request.get("full_name")
    email = request.get("email")
    password = request.get("password")
    
    if not full_name:
        raise HTTPException(status_code=400, detail="full_name is required")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    if not password:
        raise HTTPException(status_code=400, detail="password is required")
    
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    
    from app.auth import hash_password
    hashed_password = hash_password(password)
    
    
    new_user = User(
        role_id=2,  # Security Team
        researcher_type="Internal",
        full_name=full_name,
        email=email,
        phone_number=request.get("phone_number"),
        position=request.get("position"),
        password_hash=hashed_password,
        status="Active"  
    )
    
    db.add(new_user)
    
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create security team member: {str(e)}"
        )
    
    return {
        "success": True,
        "message": f"Security Team member {full_name} created successfully",
        "data": {
            "id": new_user.id,
            "full_name": new_user.full_name,
            "email": new_user.email,
            "phone_number": new_user.phone_number,
            "position": new_user.position,
            "role_id": new_user.role_id,
            "status": new_user.status,
            "created_at": new_user.created_at
        }
    }


# PUT /admin/users/{id} - UPDATE USER DATA (ADMIN ONLY)

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    request: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update user data by ID (Admin only).
    """
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )
    
    
    if "full_name" in request:
        user.full_name = request["full_name"]
    if "email" in request:
        
        existing = db.query(User).filter(
            User.email == request["email"],
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Email already used by another user"
            )
        user.email = request["email"]
    if "phone_number" in request:
        user.phone_number = request["phone_number"]
    if "position" in request:
        user.position = request["position"]
    if "office_location" in request:
        user.office_location = request["office_location"]
    if "department" in request:
        department = db.query(Department).filter(
            Department.name == request["department"]
        ).first()
        if not department:
            department = Department(name=request["department"])
            db.add(department)
            db.flush()
        user.department_id = department.id
    if "company" in request:
        user.company = request["company"]
    if "employee_id" in request:
        user.employee_id = request["employee_id"]
    
    user.updated_at = datetime.now()
    
    db.commit()
    db.refresh(user)
    
    
    role = db.query(Role).filter(Role.id == user.role_id).first()
    department = db.query(Department).filter(Department.id == user.department_id).first()
    
    return {
        "success": True,
        "message": f"User {user.full_name} updated successfully",
        "data": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "position": user.position,
            "office_location": user.office_location,
            "department_name": department.name if department else None,
            "role_name": role.name if role else None,
            "status": user.status,
            "updated_at": user.updated_at
        }
    }

# PUT /admin/users/{id}/status - UPDATE USER STATUS (ADMIN ONLY)

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    request: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update user status by ID (Admin only).
    Status options: active, inactive
    """
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )

    
    status = request.get("status")
    if not status:
        raise HTTPException(
            status_code=400,
            detail="status is required (active or inactive)"
        )
    
    if status not in ["active", "inactive"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid status. Must be 'active' or 'inactive'"
        )
    
    
    if status == "active":
        user.status = "Active"
    elif status == "inactive":
        user.status = "Inactive"
    
    user.updated_at = datetime.now()
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": f"User {user.full_name} status updated to {status}",
        "data": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "status": user.status,
            "updated_at": user.updated_at
        }
    }

# GET /admin/users/{id} - GET USER DETAIL (ADMIN ONLY)
@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get user detail by ID (Admin only).
    """

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User with ID {user_id} not found"
        )
    

    role = db.query(Role).filter(Role.id == user.role_id).first()
    

    department = db.query(Department).filter(Department.id == user.department_id).first()
    

    documents = db.query(UserDocument).filter(UserDocument.user_id == user.id).all()
    

    total_reports = db.query(Report).filter(Report.user_id == user.id).count()
    accepted_reports = db.query(Report).filter(
        Report.user_id == user.id,
        Report.status == "Accepted"
    ).count()
    rejected_reports = db.query(Report).filter(
        Report.user_id == user.id,
        Report.status == "Rejected"
    ).count()
    

    doc_list = []
    for doc in documents:
        doc_type = db.query(DocumentType).filter(DocumentType.id == doc.document_type_id).first()
        doc_list.append({
            "id": doc.id,
            "document_type": doc_type.name if doc_type else None,
            "file_name": doc.file_name,
            "object_name": doc.object_name,
            "file_size": doc.file_size,
            "content_type": doc.content_type,
            "created_at": doc.created_at
        })
    
    return {
        "success": True,
        "data": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "phone_number": user.phone_number,
            "researcher_type": user.researcher_type,
            "employee_id": user.employee_id,
            "company": user.company,
            "position": user.position,
            "office_location": user.office_location,
            "role_id": user.role_id,
            "role_name": role.name if role else None,
            "department_id": user.department_id,
            "department_name": department.name if department else None,
            "total_point": user.total_point,
            "status": user.status,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "documents": doc_list,
            "statistics": {
                "total_reports": total_reports,
                "accepted_reports": accepted_reports,
                "rejected_reports": rejected_reports
            }
        }
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