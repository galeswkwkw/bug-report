from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.services.notification_service import NotificationService
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
import uuid
import os

from app.database import SessionLocal
from app.models import User, Role, Department, UserDocument, DocumentType
from app.schemas import (
    RegisterInternalRequest,
    RegisterExternalRequest,
    LoginRequest,
    LoginResponse,
    RegisterResponse
)
from app.auth import hash_password, verify_password, create_access_token
from app.minio_client import minio_client
from app.config import Config

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Unified registration endpoint for internal and external researchers.
    NO FILE UPLOAD - use /auth/upload-documents separately.
    """
    researcher_type = request.get("researcher_type", "").lower()
    if researcher_type not in ["internal", "external"]:
        raise HTTPException(
            status_code=400,
            detail="researcher_type must be 'internal' or 'external'"
        )
    
    email = request.get("email")
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password = request.get("password")
    confirm_password = request.get("confirm_password")
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    role = db.query(Role).filter(Role.name == "Researcher").first()
    if not role:
        raise HTTPException(status_code=500, detail="Researcher role not found. Please run seed data.")
    
    user_data = {
        "role_id": role.id,
        "researcher_type": researcher_type.capitalize(),
        "full_name": request.get("full_name"),
        "email": request.get("email"),
        "password_hash": hash_password(password),
        "status": "Pending"
    }
    
    if researcher_type == "internal":
        if not request.get("employee_id"):
            raise HTTPException(status_code=400, detail="employee_id required for internal researcher")
        if not request.get("department"):
            raise HTTPException(status_code=400, detail="department required for internal researcher")
        
        department = db.query(Department).filter(Department.name == request.get("department")).first()
        if not department:
            department = Department(name=request.get("department"))
            db.add(department)
            db.flush()
        
        user_data.update({
            "employee_id": request.get("employee_id"),
            "department_id": department.id,
            "company": None,
            "phone_number": request.get("phone_number")
        })
    else:
        if not request.get("company"):
            raise HTTPException(status_code=400, detail="company required for external researcher")
        if not request.get("phone_number"):
            raise HTTPException(status_code=400, detail="phone_number required for external researcher")
        
        user_data.update({
            "company": request.get("company"),
            "phone_number": request.get("phone_number"),
            "employee_id": None,
            "department_id": None
        })
    
    new_user = User(**user_data)
    db.add(new_user)
    
    try:
        db.commit()
        db.refresh(new_user)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")
    
    admin = db.query(User).filter(User.role_id == 1).first()
    if admin:
        from app.services.notification_service import NotificationService
        NotificationService.create_registration_notification(
            db=db,
            admin_id=admin.id,
            user_name=new_user.full_name
        )
    
    return RegisterResponse(
        success=True,
        message="Registration successful. Please upload your KTP and NDA documents via /auth/upload-documents",
        status="Pending",
        user_id=new_user.id
    )


# ============================================================
# POST /auth/login
# ============================================================
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint - returns JWT token
    """
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if user.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Please wait for admin approval."
        )
    
    access_token_expires = timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role_id},
        expires_delta=access_token_expires
    )
    
    role_name = db.query(Role).filter(Role.id == user.role_id).first()
    department_name = db.query(Department).filter(Department.id == user.department_id).first()
    
    return LoginResponse(
        success=True,
        message="Login successful",
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "researcher_type": user.researcher_type,
            "role": role_name.name if role_name else None,
            "department": department_name.name if department_name else None,
            "status": user.status,
            "total_point": user.total_point
        }
    )


# ============================================================
# GET /roles
# ============================================================
@router.get("/roles")
async def get_roles(db: Session = Depends(get_db)):
    """
    Get all roles
    """
    roles = db.query(Role).all()
    return {"success": True, "data": [{"id": r.id, "name": r.name} for r in roles]}


# ============================================================
# GET /departments
# ============================================================
@router.get("/departments")
async def get_departments(db: Session = Depends(get_db)):
    """
    Get all departments
    """
    departments = db.query(Department).all()
    return {"success": True, "data": [{"id": d.id, "name": d.name} for d in departments]}


# ============================================================
# POST /auth/upload-documents - UPLOAD TANPA TOKEN
# ============================================================
@router.post("/upload-documents")
async def upload_documents(
    user_id: int = Form(...),
    ktp_file: UploadFile = File(...),
    nda_file: UploadFile = File(...),
    cv_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    Upload documents for registration (NO AUTH REQUIRED).
    User must register first to get user_id.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.status != "Pending":
        raise HTTPException(
            status_code=400,
            detail=f"User status is {user.status}. Only Pending users can upload documents."
        )
    
    uploaded_files = []
    
    # ============================================================
    # UPLOAD KTP (WAJIB)
    # ============================================================
    try:
        ktp_content = await ktp_file.read()
        ktp_size = len(ktp_content)
        
        if ktp_size > Config.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="KTP file too large. Max size: 10MB")
        
        ktp_extension = os.path.splitext(ktp_file.filename)[1]
        ktp_object_name = f"user_documents/{user_id}/ktp_{uuid.uuid4().hex[:8]}{ktp_extension}"
        
        # Upload ke MinIO (tanpa bucket_name)
        minio_client.upload_file(
            object_name=ktp_object_name,
            file_content=ktp_content,
            content_type=ktp_file.content_type
        )
        
        ktp_doc_type = db.query(DocumentType).filter(DocumentType.name == "KTP").first()
        if not ktp_doc_type:
            ktp_doc_type = DocumentType(name="KTP", required=True)
            db.add(ktp_doc_type)
            db.flush()
        
        ktp_doc = UserDocument(
            user_id=user_id,
            document_type_id=ktp_doc_type.id,
            file_name=ktp_file.filename,
            object_name=ktp_object_name,
            bucket_name="uploads",
            file_size=ktp_size,
            content_type=ktp_file.content_type or "image/jpeg"
        )
        db.add(ktp_doc)
        uploaded_files.append({"type": "KTP", "status": "uploaded"})
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"KTP upload failed: {str(e)}")
    
    # ============================================================
    # UPLOAD NDA (WAJIB)
    # ============================================================
    try:
        nda_content = await nda_file.read()
        nda_size = len(nda_content)
        
        if nda_size > Config.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="NDA file too large. Max size: 10MB")
        
        nda_extension = os.path.splitext(nda_file.filename)[1]
        nda_object_name = f"user_documents/{user_id}/nda_{uuid.uuid4().hex[:8]}{nda_extension}"
        
        # Upload ke MinIO (tanpa bucket_name)
        minio_client.upload_file(
            object_name=nda_object_name,
            file_content=nda_content,
            content_type=nda_file.content_type
        )
        
        nda_doc_type = db.query(DocumentType).filter(DocumentType.name == "NDA").first()
        if not nda_doc_type:
            nda_doc_type = DocumentType(name="NDA", required=True)
            db.add(nda_doc_type)
            db.flush()
        
        nda_doc = UserDocument(
            user_id=user_id,
            document_type_id=nda_doc_type.id,
            file_name=nda_file.filename,
            object_name=nda_object_name,
            bucket_name="uploads",
            file_size=nda_size,
            content_type=nda_file.content_type or "application/pdf"
        )
        db.add(nda_doc)
        uploaded_files.append({"type": "NDA", "status": "uploaded"})
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"NDA upload failed: {str(e)}")
    
    # ============================================================
    # UPLOAD CV (OPSIONAL)
    # ============================================================
    if cv_file and cv_file.filename:
        try:
            cv_content = await cv_file.read()
            cv_size = len(cv_content)
            
            if cv_size > Config.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="CV file too large. Max size: 10MB")
            
            cv_extension = os.path.splitext(cv_file.filename)[1]
            cv_object_name = f"user_documents/{user_id}/cv_{uuid.uuid4().hex[:8]}{cv_extension}"
            
            # Upload ke MinIO (tanpa bucket_name)
            minio_client.upload_file(
                object_name=cv_object_name,
                file_content=cv_content,
                content_type=cv_file.content_type
            )
            
            cv_doc_type = db.query(DocumentType).filter(DocumentType.name == "CV").first()
            if not cv_doc_type:
                cv_doc_type = DocumentType(name="CV", required=False)
                db.add(cv_doc_type)
                db.flush()
            
            cv_doc = UserDocument(
                user_id=user_id,
                document_type_id=cv_doc_type.id,
                file_name=cv_file.filename,
                object_name=cv_object_name,
                bucket_name="uploads",
                file_size=cv_size,
                content_type=cv_file.content_type or "application/pdf"
            )
            db.add(cv_doc)
            uploaded_files.append({"type": "CV", "status": "uploaded"})
            
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"CV upload failed: {str(e)}")
    
    # ============================================================
    # COMMIT ALL
    # ============================================================
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save document metadata: {str(e)}")
    
    return {
        "success": True,
        "message": "Documents uploaded successfully",
        "user_id": user_id,
        "documents": uploaded_files,
        "status": user.status
    }