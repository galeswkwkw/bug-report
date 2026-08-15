import bleach
import re
from typing import Dict, Any, Optional


class Sanitizers:
    """Input sanitization utilities"""
    
    
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'
    ]
    
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        'img': ['src', 'alt'],
    }
    
    @staticmethod
    def sanitize_html(text: str) -> str:
        """Sanitize HTML content"""
        if not text:
            return text
        
        return bleach.clean(
            text,
            tags=Sanitizers.ALLOWED_TAGS,
            attributes=Sanitizers.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Sanitize plain text input"""
        if not text:
            return text
        
        
        text = bleach.clean(text, tags=[], strip=True)
        
        
        text = ' '.join(text.split())
        
        
        text = ''.join(char for char in text if ord(char) >= 32)
        
        return text.strip()
    
    @staticmethod
    def sanitize_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize user registration/login data
        """
        sanitized = {}
        
        
        field_map = {
            'email': Sanitizers._sanitize_email,
            'full_name': Sanitizers._sanitize_name,
            'password': Sanitizers._sanitize_password,
            'confirm_password': Sanitizers._sanitize_password,
            'company': Sanitizers._sanitize_text,
            'phone_number': Sanitizers._sanitize_phone,
            'employee_id': Sanitizers._sanitize_employee_id,
            'department': Sanitizers._sanitize_text,
            'researcher_type': Sanitizers._sanitize_text,
            'current_password': Sanitizers._sanitize_password,
            'new_password': Sanitizers._sanitize_password,
            'feedback': Sanitizers._sanitize_text, 
        }
        
        for key, value in data.items():
            if key in field_map:
                sanitized[key] = field_map[key](value)
            else:
                
                if isinstance(value, str):
                    sanitized[key] = Sanitizers.sanitize_text(value)
                else:
                    sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def _sanitize_email(email: str) -> str:
        """Sanitize email"""
        if not email:
            return email
        return email.strip().lower()
    
    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize name"""
        if not name:
            return name
        
        
        name = bleach.clean(name, tags=[], strip=True)
        
        
        name = ' '.join(name.split())
        
        
        name = re.sub(r'[^a-zA-Z\s\-\']', '', name)
        
        return name.strip()
    
    @staticmethod
    def _sanitize_password(password: str) -> str:
        """Password should be kept as-is for verification"""
        return password
    
    @staticmethod
    def _sanitize_phone(phone: str) -> str:
        """Sanitize phone number"""
        if not phone:
            return phone
        
        
        phone = re.sub(r'[^\d\+]', '', phone)
        return phone
    
    @staticmethod
    def _sanitize_employee_id(emp_id: str) -> str:
        """Sanitize employee ID"""
        if not emp_id:
            return emp_id
        
        
        emp_id = re.sub(r'[^A-Za-z0-9\-]', '', emp_id)
        return emp_id.strip()
    
    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Generic text sanitization"""
        if not text:
            return text
        
        
        text = bleach.clean(text, tags=[], strip=True)
        
        
        text = ' '.join(text.split())
        
        return text.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for uploads"""
        if not filename:
            return filename
        
        
        filename = filename.replace('/', '').replace('\\', '')
        
        
        filename = re.sub(r'[^a-zA-Z0-9\.\-_]', '', filename)
        
        return filename