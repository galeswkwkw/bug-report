import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import User, PasswordResetToken
from app.services.email_service import send_reset_password_email
from app.services.email_service import EmailService
class PasswordResetService:
    TOKEN_EXPIRY_MINUTES = 20
    
    @staticmethod
    def generate_token() -> str:
        """Generate secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))
    
    @staticmethod
    def create_reset_token(db: Session, user_id: int) -> PasswordResetToken:
        """Create password reset token for user"""
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expired_at > datetime.utcnow()
        ).update({"expired_at": datetime.utcnow()})
        
        token = PasswordResetService.generate_token()
        expired_at = datetime.utcnow() + timedelta(minutes=PasswordResetService.TOKEN_EXPIRY_MINUTES)
        
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expired_at=expired_at,
            used_at=None
        )
        
        db.add(reset_token)
        db.commit()
        db.refresh(reset_token)
        
        return reset_token
    
    @staticmethod
    def validate_token(db: Session, token: str) -> dict:
        """Validate reset token"""
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token
        ).first()
        
        if not reset_token:
            return {"valid": False, "message": "Invalid reset token"}
        
        if reset_token.used_at is not None:
            return {"valid": False, "message": "Token has already been used"}
        
        if reset_token.expired_at < datetime.utcnow():
            return {"valid": False, "message": "Reset password link has expired"}
        
        return {
            "valid": True, 
            "expires_at": reset_token.expired_at
        }
    
    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> dict:
        """Reset user password"""
    
        validation = PasswordResetService.validate_token(db, token)
        if not validation["valid"]:
            return {"success": False, "message": validation["message"]}
        
    
        reset_token = db.query(PasswordResetToken).filter(
            PasswordResetToken.token == token
        ).first()
        
    
        user = db.query(User).filter(User.id == reset_token.user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
    
        from app.auth import hash_password
        user.password_hash = hash_password(new_password)
        
    
        reset_token.used_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "Password has been reset successfully"}