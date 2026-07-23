from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from fastapi import File, UploadFile

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
    refresh_token: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int
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

class AssetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    domain: str = Field(..., min_length=1, max_length=255)
    asset_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_active: bool = True


class AssetUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    domain: Optional[str] = Field(None, min_length=1, max_length=255)
    asset_type: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    is_active: Optional[bool] = None

class AssetResponse(BaseModel):
    id: int
    name: str
    domain: str
    asset_type: Optional[str] = None 
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ReportCreateRequest(BaseModel):
    asset_id: int
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    steps_to_reproduce: str = Field(..., min_length=1)
    steps_to_resolve: Optional[str] = None
    impact: Optional[str] = None
    affected_endpoint: Optional[str] = Field(None, max_length=500) 

class ReportResponse(BaseModel):
    id: int
    user_id: int
    asset_id: int
    reviewer_id: Optional[int] = None
    reviewer: Optional[dict] = None
    title: str
    category: str
    description: str
    steps_to_reproduce: str
    steps_to_resolve: Optional[str]
    impact: Optional[str]
    affected_endpoint: Optional[str] = None 
    severity: Optional[str] = None
    point: int
    status: str
    review_comment: Optional[str]
    reject_reason: Optional[str]
    assignment_comment: Optional[str] = None 
    reviewed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    asset_name: Optional[str] = None
    user_name: Optional[str] = None
    can_edit: bool = False

class ReportEvidenceResponse(BaseModel):
    id: int
    report_id: int
    file_name: str
    object_name: str
    bucket_name: str
    file_size: int
    content_type: str
    created_at: datetime
    url: Optional[str] = None

class ReportEvidenceUpdateRequest(BaseModel):
    file: UploadFile = File(...)

class ReportUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, pattern="^(Accepted|Rejected)$")


class ReviewRequest(BaseModel):
    result: str = Field(..., pattern="^(accepted|rejected)$")
    severity: Optional[str] = Field(None, pattern="^(Critical|High|Medium|Low|Informational)$")
    comment: Optional[str] = None
    reject_reason: Optional[str] = None


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    type: str
    reference_id: Optional[int] = None
    is_read: bool
    created_at: datetime

class NotificationListResponse(BaseModel):
    page: int
    limit: int
    total: int
    data: List[NotificationResponse]

class AssignReportRequest(BaseModel):
    security_team_id: int
    comment: Optional[str] = None  

class ReportUpdateByResearcherRequest(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    steps_to_resolve: Optional[str] = None
    impact: Optional[str] = None
    severity: Optional[str] = Field(None, pattern="^(Critical|High|Medium|Low|Informational)$")