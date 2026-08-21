# app/services/session_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from fastapi import HTTPException, status
import uuid

from app.models import User, UserSession
from app.config import Config


class SessionService:
    """Service untuk mengelola session login"""
    
    MAX_SESSIONS = {
        1: 3,  
        2: 3,  
        3: 3,    
    }
    
    @staticmethod
    def get_max_sessions(role_id: int) -> int:
        """Dapatkan batas maksimal session berdasarkan role"""
        return SessionService.MAX_SESSIONS.get(role_id, 3)
    
    @staticmethod
    def create_session(
        db: Session,
        user_id: int,
        refresh_token: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> UserSession:
        """
        Buat session baru untuk user.
        Otomatis hapus session lama jika melebihi batas.
        """
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        max_sessions = SessionService.get_max_sessions(user.role_id)
        
        
        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        
        if active_sessions >= max_sessions:
            
            oldest_session = db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
                UserSession.expires_at > datetime.utcnow()
            ).order_by(UserSession.created_at.asc()).first()
            
            if oldest_session:
                
                oldest_session.is_active = False
                db.commit()
                print(f"🔒 Session {oldest_session.id} expired karena limit {max_sessions} tercapai")
        
        
        session_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
        
        new_session = UserSession(
            user_id=user_id,
            session_token=session_id,
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            expires_at=expires_at
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        return new_session
    
    @staticmethod
    def validate_session(db: Session, session_token: str) -> UserSession:
        """Validasi apakah session masih aktif"""
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid"
            )
        
        return session
    
    @staticmethod
    def logout_session(db: Session, session_token: str) -> bool:
        """Logout session tertentu"""
        session = db.query(UserSession).filter(
            UserSession.session_token == session_token
        ).first()
        
        if session:
            session.is_active = False
            db.commit()
            return True
        return False
    
    @staticmethod
    def logout_all_sessions(db: Session, user_id: int) -> int:
        """Logout semua session user (logout from all devices)"""
        result = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True
        ).update({"is_active": False})
        
        db.commit()
        return result
    
    @staticmethod
    def get_active_sessions(db: Session, user_id: int) -> list:
        """Dapatkan semua session aktif user"""
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user_id,
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).order_by(UserSession.created_at.desc()).all()
        
        return [
            {
                "id": s.id,
                "session_token": s.session_token[-8:],  
                "ip_address": s.ip_address,
                "user_agent": s.user_agent[:50] + "..." if s.user_agent and len(s.user_agent) > 50 else s.user_agent,
                "created_at": s.created_at,
                "expires_at": s.expires_at
            }
            for s in sessions
        ]
    
    @staticmethod
    def clean_expired_sessions(db: Session) -> int:
        """Bersihkan session yang sudah expired"""
        result = db.query(UserSession).filter(
            UserSession.expires_at < datetime.utcnow()
        ).update({"is_active": False})
        
        db.commit()
        return result