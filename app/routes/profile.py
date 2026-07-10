from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
import uuid
import os

from app.database import SessionLocal
from app.models import User, Role, Department, UserDocument, DocumentType
from app.schemas import (  
    ProfileResponse,
    ProfileUpdateRequest,
    DocumentUploadResponse
)
from app.auth import get_current_active_user, get_current_user
from app.minio_client import minio_client
from app.config import Config

router = APIRouter(prefix="/profile", tags=["Profile"])



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# GET /profile
@router.get("", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user profile
    """
    role = db.query(Role).filter(Role.id == current_user.role_id).first()
    
    department = db.query(Department).filter(Department.id == current_user.department_id).first()
    documents = db.query(UserDocument).filter(UserDocument.user_id == current_user.id).all()
    
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
    
    return ProfileResponse(
        id=current_user.id,
        role_id=current_user.role_id,
        role_name=role.name if role else None,
        department_id=current_user.department_id,
        department_name=department.name if department else None,
        researcher_type=current_user.researcher_type,
        employee_id=current_user.employee_id,
        company=current_user.company,
        full_name=current_user.full_name,
        email=current_user.email,
        phone_number=current_user.phone_number,
        total_point=current_user.total_point,
        status=current_user.status,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        documents=doc_list,
        position=user.position,
        office_location=user.office_location
    )

# PUT /profile
@router.put("")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile
    """
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.full_name:
        user.full_name = request.full_name
    if request.phone_number:
        user.phone_number = request.phone_number
    if request.company:
        user.company = request.company
    if request.position:
        user.position = request.position
    if request.office_location:
        user.office_location = request.office_location
    
    if request.department:
        department = db.query(Department).filter(Department.name == request.department).first()
        if not department:
            department = Department(name=request.department)
            db.add(department)
            db.flush()
        user.department_id = department.id
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "message": "Profile updated successfully",
        "user_id": user.id
    }
# POST /profile/documents
@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),  
    db: Session = Depends(get_db)
):
    """
    Upload user document (KTP, NDA, CV, Portfolio)
    """
    document_type_upper = document_type.upper()
    if document_type_upper not in Config.ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid document type. Allowed: {', '.join(Config.ALLOWED_DOCUMENT_TYPES)}"
        )
    
    doc_type = db.query(DocumentType).filter(
        DocumentType.name == document_type_upper
    ).first()
    
    if not doc_type:
        doc_type = DocumentType(name=document_type_upper, required=True)
        db.add(doc_type)
        db.flush()
    
    existing = db.query(UserDocument).filter(
        UserDocument.user_id == current_user.id,
        UserDocument.document_type_id == doc_type.id
    ).first()
    
    if existing:
        try:
            minio_client.client.remove_object("documents", existing.object_name)
        except:
            pass
        db.delete(existing)
        db.flush()
    
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > Config.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size: 10MB")
    
    file_extension = os.path.splitext(file.filename)[1]
    object_name = f"user_documents/{current_user.id}/{document_type_upper.lower()}_{uuid.uuid4().hex[:8]}{file_extension}"
    
    try:
        minio_result = minio_client.upload_file(
            bucket_name="documents",
            object_name=object_name,
            file_content=file_content,
            content_type=file.content_type
        )
        
        user_doc = UserDocument(
            user_id=current_user.id,
            document_type_id=doc_type.id,
            file_name=file.filename,
            object_name=object_name,
            bucket_name="documents",
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream"
        )
        
        db.add(user_doc)
        db.commit()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    return DocumentUploadResponse(
        success=True,
        message=f"{document_type} uploaded successfully",
        file_name=file.filename,
        object_name=object_name,
        document_type=document_type_upper
    )

# GET /profile/documents
@router.get("/documents")
async def get_documents(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all documents for current user
    """
    documents = db.query(UserDocument).filter(UserDocument.user_id == current_user.id).all()
    
    result = []
    for doc in documents:
        doc_type = db.query(DocumentType).filter(DocumentType.id == doc.document_type_id).first()
        
        presigned_url = minio_client.get_presigned_url(
            doc.object_name,
            expiry=3600
        )
        result.append({
            "id": doc.id,
            "document_type": doc_type.name if doc_type else None,
            "file_name": doc.file_name,
            "object_name": doc.object_name,
            "file_size": doc.file_size,
            "content_type": doc.content_type,
            "created_at": doc.created_at,
            "url": presigned_url
        })
    
    return {"success": True, "data": result}