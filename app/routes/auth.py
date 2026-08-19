from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.services.notification_service import NotificationService
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
import uuid
import os
from app.services.session_service import SessionService

from app.utils.rate_limiter import rate_limiter, get_client_ip
from fastapi import Request
from app.utils.sanitizers import Sanitizers
from app.database import SessionLocal
from app.models import User, Role, Department, UserDocument, DocumentType, PasswordResetToken  
from app.schemas import (
    RegisterInternalRequest, 
    RegisterExternalRequest, 
    LoginRequest, 
    LoginResponse, 
    RegisterResponse,
    ForgotPasswordRequest,
    ValidateResetTokenResponse,
    ResetPasswordRequest,
    ResetPasswordResponse
)
from app.auth import create_access_token, create_refresh_token, get_current_user, get_current_active_user   
from app.auth import hash_password, verify_password, create_access_token
from app.minio_client import minio_client
from app.config import Config
from app.services.password_reset_service import PasswordResetService
from app.services.email_service import EmailService


router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# app/routes/auth.py
@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Request password reset - sends email with reset link
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Email address not found. Please register first."
        )
    
    try:
        reset_token = PasswordResetService.create_reset_token(db, user.id)
        
        frontend_url = "https://fountguard.com/reset-password"
        EmailService.send_reset_password_email(
            to_email=user.email,
            reset_token=reset_token.token,
            frontend_url=frontend_url
        )
        
        return {
            "success": True,
            "message": "Password reset link has been sent to your email address."
        }
        
    except Exception as e:
        print(f"Error in forgot-password: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to send reset email. Please try again later."
        )

@router.post("/change-password")
async def change_password(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change user password (requires current password).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    current_password = request.get("current_password")
    new_password = request.get("new_password")
    confirm_password = request.get("confirm_password")
    
    if not current_password:
        raise HTTPException(status_code=400, detail="current_password is required")
    if not new_password:
        raise HTTPException(status_code=400, detail="new_password is required")
    if not confirm_password:
        raise HTTPException(status_code=400, detail="confirm_password is required")
    
    from app.auth import verify_password
    
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    from app.auth import hash_password
    
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    
    logger.info(f"🔍 BEFORE COMMIT: user_id={user.id}, must_change_password={user.must_change_password}")
    
    try:
        db.commit()
        logger.info(f"✅ Password changed for user_id={user.id}")
    except Exception as e:
        db.rollback()
        logger.error(f"❌ db.commit() ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    db.refresh(user)
    logger.info(f"🔍 AFTER COMMIT: user_id={user.id}, must_change_password={user.must_change_password}")
    
    return {
        "message": "Password changed successfully."
    }


# GET /auth/reset-password/validate
@router.get("/reset-password/validate", response_model=ValidateResetTokenResponse)
async def validate_reset_token(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validate reset token
    """
    result = PasswordResetService.validate_token(db, token)
    
    return ValidateResetTokenResponse(
        valid=result.get("valid", False),
        expires_at=result.get("expires_at"),
        message=result.get("message")
    )


# POST /auth/reset-password
@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using token
    """
    
    if request.new_password != request.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )
    
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )
    
    
    result = PasswordResetService.reset_password(
        db, 
        request.token, 
        request.new_password
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["message"]
        )
    
    return ResetPasswordResponse(
        message=result["message"]
    )
@router.post("/register", response_model=RegisterResponse)
async def register(
    request: dict,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Unified registration endpoint with rate limiting
    """
    
    sanitized_data = Sanitizers.sanitize_user_data(request)

    
    client_ip = get_client_ip(http_request)
    allowed, wait_time = rate_limiter.check(f"register_{client_ip}")
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many registration attempts. Please try again in {wait_time} seconds."
        )
    
    
    researcher_type = sanitized_data.get("researcher_type", "").lower()
    email = sanitized_data.get("email")
    full_name = sanitized_data.get("full_name")
    password = sanitized_data.get("password")
    confirm_password = sanitized_data.get("confirm_password")
    phone_number = sanitized_data.get("phone_number")
    employee_id = sanitized_data.get("employee_id")
    department_name = sanitized_data.get("department")
    company = sanitized_data.get("company")
    
    
    if researcher_type not in ["internal", "external"]:
        raise HTTPException(
            status_code=400,
            detail="researcher_type must be 'internal' or 'external'"
        )
    
    
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        rate_limiter.record_attempt(f"register_{client_ip}")
        raise HTTPException(status_code=400, detail="Email already registered")
    
    
    rate_limiter.reset(f"register_{client_ip}")
    
    
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    
    role = db.query(Role).filter(Role.name == "Bug Hunter").first()
    if not role:
        raise HTTPException(status_code=500, detail="Bug Hunter role not found. Please run seed data.")
    
    
    user_data = {
        "role_id": role.id,
        "researcher_type": researcher_type.capitalize(),
        "full_name": full_name,
        "email": email,
        "password_hash": hash_password(password),
        "status": "Pending"
    }
    
    
    if researcher_type == "internal":
        if not employee_id:
            raise HTTPException(status_code=400, detail="employee_id required for internal researcher")
        if not department_name:
            raise HTTPException(status_code=400, detail="department required for internal researcher")
        
        department = db.query(Department).filter(Department.name == department_name).first()
        if not department:
            department = Department(name=department_name)
            db.add(department)
            db.flush()
        
        user_data.update({
            "employee_id": employee_id,
            "department_id": department.id,
            "company": None,
            "phone_number": phone_number
        })
    else:
        if not company:
            raise HTTPException(status_code=400, detail="company required for external researcher")
        if not phone_number:
            raise HTTPException(status_code=400, detail="phone_number required for external researcher")
        
        user_data.update({
            "company": company,
            "phone_number": phone_number,
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
    
    
    NotificationService.create_registration_notification(
        db=db,
        user_name=new_user.full_name
    )
    
    return RegisterResponse(
        success=True,
        message="Registration successful. Please upload your NDA documents via /auth/upload-documents",
        status="Pending",
        user_id=new_user.id
    )

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Login endpoint - returns JWT token with rate limiting
    """
    sanitized_email = Sanitizers._sanitize_email(request.email)
    
    client_ip = get_client_ip(http_request)
    allowed, wait_time = rate_limiter.check(f"login_{client_ip}")
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many login attempts. Please try again in {wait_time} seconds."
        )
    
    user = db.query(User).filter(User.email == sanitized_email).first()
    if not user:
        rate_limiter.record_attempt(f"login_{client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(request.password, user.password_hash):
        rate_limiter.record_attempt(f"login_{client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    rate_limiter.reset(f"login_{client_ip}")
    
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
    
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role_id}
    )
    
    role_name = db.query(Role).filter(Role.id == user.role_id).first()
    department_name = db.query(Department).filter(Department.id == user.department_id).first()
    client_ip = get_client_ip(http_request)
    user_agent = http_request.headers.get("user-agent", "Unknown")
    
    session = SessionService.create_session(
        db=db,
        user_id=user.id,
        refresh_token=refresh_token,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return LoginResponse(
        success=True,
        message="Login successful",
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=Config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "researcher_type": user.researcher_type,
            "role": role_name.name if role_name else None,
            "department": department_name.name if department_name else None,
            "status": user.status,
            "total_point": user.total_point,
            "must_change_password": user.must_change_password,
            "session_id": session.session_token  
        }
    )



# GET /roles
@router.get("/roles")
async def get_roles(db: Session = Depends(get_db)):
    """
    Get all roles
    """
    roles = db.query(Role).all()
    return {"success": True, "data": [{"id": r.id, "name": r.name} for r in roles]}


# GET /departments
@router.get("/departments")
async def get_departments(db: Session = Depends(get_db)):
    """
    Get all departments
    """
    departments = db.query(Department).all()
    return {"success": True, "data": [{"id": d.id, "name": d.name} for d in departments]}


# POST /auth/upload-documents - UPLOAD TANPA TOKEN

@router.post("/upload-documents")
async def upload_documents(
    user_id: int = Form(...),
    nda_file: UploadFile = File(...),  
    ktp_file: UploadFile = File(None),  
    cv_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    """
    Upload documents for registration (NO AUTH REQUIRED).
    User must register first to get user_id.
    - NDA: Wajib
    - KTP: Opsional
    - CV: Opsional
    - Allowed formats: pdf, png, jpg
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
    
    
    def validate_file_extension(filename: str):
        allowed_extensions = [".pdf", ".png", ".jpg", ".jpeg"]
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File format not allowed. Allowed formats: pdf, png, jpg. Your file: {filename}"
            )
    
    
    # UPLOAD KTP (OPSIONAL)
    
    if ktp_file and ktp_file.filename:
        try:
            
            validate_file_extension(ktp_file.filename)
            
            ktp_content = await ktp_file.read()
            ktp_size = len(ktp_content)
            
            if ktp_size == 0:
                raise HTTPException(status_code=400, detail="KTP file is empty!")
            
            if ktp_size > Config.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"KTP file too large. Max size: 10MB")
            
            ktp_extension = os.path.splitext(ktp_file.filename)[1]
            ktp_object_name = f"user_documents/{user_id}/ktp_{uuid.uuid4().hex[:8]}{ktp_extension}"
            
            minio_client.upload_file(
                object_name=ktp_object_name,
                file_content=ktp_content,
                content_type=ktp_file.content_type
            )
            
            ktp_doc_type = db.query(DocumentType).filter(DocumentType.name == "KTP").first()
            if not ktp_doc_type:
                ktp_doc_type = DocumentType(name="KTP", required=False)
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
    
    
    # UPLOAD NDA (WAJIB)
    
    try:
       
        validate_file_extension(nda_file.filename)
        
        nda_content = await nda_file.read()
        nda_size = len(nda_content)
        
        if nda_size == 0:
            raise HTTPException(status_code=400, detail="NDA file is empty!")
        
        if nda_size > Config.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"NDA file too large. Max size: 10MB")
        
        nda_extension = os.path.splitext(nda_file.filename)[1]
        nda_object_name = f"user_documents/{user_id}/nda_{uuid.uuid4().hex[:8]}{nda_extension}"
        
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
    
    
    # UPLOAD CV (OPSIONAL)
    
    if cv_file and cv_file.filename:
        try:
            
            validate_file_extension(cv_file.filename)
            
            cv_content = await cv_file.read()
            cv_size = len(cv_content)
            
            if cv_size == 0:
                raise HTTPException(status_code=400, detail="CV file is empty!")
            
            if cv_size > Config.MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"CV file too large. Max size: 10MB")
            
            cv_extension = os.path.splitext(cv_file.filename)[1]
            cv_object_name = f"user_documents/{user_id}/cv_{uuid.uuid4().hex[:8]}{cv_extension}"
            
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
    
    
    # COMMIT ALL
    
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

@router.post("/logout")
async def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user), 
    token: str = Depends(oauth2_scheme) 
):
    """
    Logout user - cukup kirim JWT token saja (FE tidak perlu session_id)
    """
    from app.models import UserSession
    
   
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    
    session = db.query(UserSession).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    
    if session:
        session.is_active = False
        db.commit()
        return {"message": "Logged out successfully"}
    
    return {"message": "Logged out successfully (no active session found)"}


@router.post("/logout-all")
async def logout_all_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout dari semua perangkat (logout all sessions)
    """
    count = SessionService.logout_all_sessions(db, current_user.id)
    
    return {
        "message": f"Logged out from all {count} devices successfully"
    }


@router.get("/sessions")
async def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Dapatkan daftar semua session aktif user
    """
    sessions = SessionService.get_active_sessions(db, current_user.id)
    
    max_sessions = SessionService.get_max_sessions(current_user.role_id)
    
    return {
        "success": True,
        "max_sessions": max_sessions,
        "current_sessions": len(sessions),
        "data": sessions
    } 