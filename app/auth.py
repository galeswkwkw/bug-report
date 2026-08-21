from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import bcrypt
from app.utils.rate_limiter import RateLimiter, rate_limiter, get_client_ip
from app.utils.sanitizers import Sanitizers

from app.config import Config
from app.database import SessionLocal, get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode('utf-8')[:72]
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id: int = payload.get("sub")
        session_id: str = payload.get("session_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        
        
        
        
        from app.models import UserSession
        from app.services.session_service import SessionService
        
        active_session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.session_token == session_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if not active_session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or not found. Please login again."
            )
        
        
        max_sessions = SessionService.get_max_sessions(user.role_id)
        active_sessions_count = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        if active_sessions_count > max_sessions:
            oldest_session = db.query(UserSession).filter(
                UserSession.user_id == user.id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow(),
                UserSession.id != active_session.id
            ).order_by(UserSession.created_at.asc()).first()
            
            if oldest_session:
                oldest_session.is_active = False
                db.commit()
                print(f"🔒 Auto-logout session ID {oldest_session.id} karena melebihi batas {max_sessions}")
        
        
        return user
    finally:
        db.close()

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.role_id == 4:
        return current_user
    
    if current_user.status != "Active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active. Please wait for admin approval."
        )
    return current_user

def get_current_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role_id not in [1, 4]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def get_current_security(current_user: User = Depends(get_current_active_user)):
    if current_user.role_id not in [2, 4]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Team access required"
        )
    return current_user

def get_current_admin_or_security(current_user: User = Depends(get_current_active_user)):
    if current_user.role_id not in [1, 2, 4]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Security Team access required"
        )
    return current_user

def check_self_or_admin(current_user: User, target_user_id: int, db: Session):
    """
    Check if current user is admin or the target user themselves.
    """
    
    role = db.query(Role).filter(Role.id == current_user.role_id).first()
    if role and role.name == "Admin":
        return True
    
    
    if current_user.id == target_user_id:
        return True
    
    return False

def get_current_user_with_session(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Get current user AND validate session.
    Juga otomatis hapus session terlama jika melebihi batas.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

   
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

   
   
    active_session = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).first()

  
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or not found. Please login again."
        )

   
    max_sessions = SessionService.get_max_sessions(user.role_id)
    
    active_sessions_count = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.utcnow()
    ).count()

    
    if active_sessions_count > max_sessions:
        
        oldest_session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow(),
            UserSession.id != active_session.id 
        ).order_by(UserSession.created_at.asc()).first()

        if oldest_session:
            oldest_session.is_active = False
            db.commit()
            print(f"🔒 Auto-logout session ID {oldest_session.id} karena melebihi batas {max_sessions}")

    return user