from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime

# AUTH SCHEMAS

class RegisterInternalRequest(BaseModel):
    researcher_type: str = "internal"
    employee_id: str
    full_name: str
    email: EmailStr
    department: str
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class RegisterExternalRequest(BaseModel):
    researcher_type: str = "external"
    company: str
    full_name: str
    email: EmailStr
    phone_number: str
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class RegisterResponse(BaseModel):
    success: bool
    message: str
    status: str
    user_id: Optional[int] = None
    documents_uploaded: Optional[dict] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    user: dict

class RegisterResponse(BaseModel):
    success: bool
    message: str
    status: str
    user_id: Optional[int] = None

# PROFILE SCHEMAS


class ProfileResponse(BaseModel):
    id: int
    role_id: int
    role_name: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    researcher_type: str
    employee_id: Optional[str] = None
    company: Optional[str] = None
    full_name: str
    email: str
    phone_number: Optional[str] = None
    position: Optional[str] = None
    office_location: Optional[str] = None
    total_point: int
    status: str
    created_at: datetime
    updated_at: datetime
    documents: Optional[List[dict]] = []

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    department: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    office_location: Optional[str] = None


# DOCUMENT SCHEMAS

class DocumentUploadResponse(BaseModel):
    success: bool
    message: str
    file_name: str
    object_name: str
    document_type: str

class DocumentResponse(BaseModel):
    id: int
    document_type: str
    file_name: str
    object_name: str
    file_size: int
    content_type: str
    created_at: datetime

# ADMIN SCHEMAS


class PendingUserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    researcher_type: str
    company: Optional[str] = None
    employee_id: Optional[str] = None
    department_name: Optional[str] = None
    created_at: datetime
    documents: List[dict]
    status: str

class AdminActionResponse(BaseModel):
    success: bool
    message: str
    user_id: int
    new_status: str