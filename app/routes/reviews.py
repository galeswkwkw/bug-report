from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import Report, Asset, User, PointRule, ReportEvidence
from app.schemas import ReviewRequest, ReportResponse
from app.auth import get_current_active_user
from app.minio_client import minio_client

router = APIRouter(prefix="/reviews", tags=["Reviews"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET CURRENT SECURITY TEAM (role_id = 2)
def get_current_security(current_user: User = Depends(get_current_active_user)):
    if current_user.role_id != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security Team access required"
        )
    return current_user

def get_current_admin_or_security(current_user: User = Depends(get_current_active_user)):
    if current_user.role_id not in [1, 2]:  
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Security Team access required"
        )
    return current_user


# GET /reviews/my-assigned - LIST ASSIGNED REPORTS (ADMIN & SECURITY)
@router.get("/my-assigned")
async def get_my_assigned_reviews(
    current_user: User = Depends(get_current_admin_or_security),
    db: Session = Depends(get_db),
    status: Optional[str] = None 
):
    """
    Get all reports assigned to current user (Security Team) or all assigned reports (Admin).
    - Security Team: hanya report yang di-assign ke dirinya sendiri
    - Admin: semua report yang statusnya 'Assigned' atau 'In Review'
    
    Query Parameters:
    - status: filter by status (assigned, in_review, reviewed)
    """
    
    if current_user.role_id == 1:  
        query = db.query(Report).filter(
            Report.status.in_(["Assigned", "In Review", "Accepted", "Rejected"])
        )
    else:  
        query = db.query(Report).filter(
            Report.assigned_to == current_user.id,
            Report.status.in_(["Assigned", "In Review", "Accepted", "Rejected"])
        )
 
    if status == "assigned":
        query = query.filter(Report.status == "Assigned")
    elif status == "in_review":
        query = query.filter(Report.status == "In Review")
    elif status == "reviewed":
        query = query.filter(Report.status.in_(["Accepted", "Rejected"]))
    
    reports = query.order_by(Report.created_at.desc()).all()
    
    result = []
    for report in reports:
        asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
        user = db.query(User).filter(User.id == report.user_id).first()
        
        result.append({
            "id": report.id,
            "title": report.title,
            "asset": asset.domain if asset else None,
            "asset_name": asset.name if asset else None,
            "reporter": user.full_name if user else None,
            "severity": report.severity,
            "status": report.status,
            "reviewed_at": report.reviewed_at,  
            "created_at": report.created_at,
            "updated_at": report.updated_at
        })
    
    return {
        "success": True,
        "count": len(result),
        "data": result
    }

# PUT /reviews/{id}/start-review - START REVIEW
@router.put("/{report_id}/start-review")
async def start_review(
    report_id: int,
    current_user: User = Depends(get_current_security),
    db: Session = Depends(get_db)
):
    """
    Start review process for a report (Security Team only).
    Only reports with status 'Assigned' can be started.
    Status will change to 'In Review'.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.assigned_to != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="This report is not assigned to you"
        )
    
    if report.status != "Assigned":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start review for report with status: {report.status}. Only Assigned reports can be started."
        )
    
    report.status = "In Review"
    report.reviewed_at = datetime.now()
    report.updated_at = datetime.now()
    
    db.commit()
    db.refresh(report)
    
    return {
        "success": True,
        "message": f"Review started for report {report_id}",
        "report_id": report.id,
        "status": report.status, 
        "started_at": report.reviewed_at
    }
# PUT /reviews/{id} - REVIEW REPORT (ACCEPT/REJECT)
@router.put("/{report_id}", response_model=ReportResponse)
async def review_report(
    report_id: int,
    request: ReviewRequest,
    current_user: User = Depends(get_current_security),
    db: Session = Depends(get_db)
):
    """
    Review report by Security Team.
    - Accept: set severity, comment → point otomatis dihitung
    - Reject: set reject_reason, comment → point tetap 0
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.assigned_to != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="This report is not assigned to you"
        )
    
    if report.status not in ["Assigned", "In Review"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot review report with status: {report.status}. Only Assigned or In Review reports can be reviewed."
        )
    
    if request.result not in ["accepted", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Result must be 'accepted' or 'rejected'"
        )
    
    if request.result == "accepted":
        if not request.severity:
            raise HTTPException(
                status_code=400,
                detail="Severity is required when accepting a report"
            )
        
        valid_severities = ["Critical", "High", "Medium", "Low", "Informational"]
        if request.severity not in valid_severities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: {', '.join(valid_severities)}"
            )
        
        report.status = "Accepted"
        report.severity = request.severity
        report.review_comment = request.comment
        report.reviewer_id = current_user.id
        report.reviewed_at = datetime.now()
        report.accepted_at = datetime.now()  # 🔥 TAMBAHKAN!
        
        point_rule = db.query(PointRule).filter(PointRule.severity == request.severity).first()
        report.point = point_rule.point if point_rule else 0
        
        user = db.query(User).filter(User.id == report.user_id).first()
        if user:
            user.total_point += report.point
            db.add(user)
    
    elif request.result == "rejected":
        if not request.reject_reason:
            raise HTTPException(
                status_code=400,
                detail="Reject reason is required when rejecting a report"
            )
        
        report.status = "Rejected"
        report.reject_reason = request.reject_reason
        report.review_comment = request.comment
        report.reviewer_id = current_user.id
        report.reviewed_at = datetime.now()
        report.rejected_at = datetime.now()  # 🔥 TAMBAHKAN!
        report.point = 0
    
    report.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(report)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to review report: {str(e)}"
        )
    
    asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
    user = db.query(User).filter(User.id == report.user_id).first()
    
    return ReportResponse(
        id=report.id,
        user_id=report.user_id,
        asset_id=report.asset_id,
        reviewer_id=report.reviewer_id,
        title=report.title,
        category=report.category,
        description=report.description,
        steps_to_reproduce=report.steps_to_reproduce,
        steps_to_resolve=report.steps_to_resolve,
        impact=report.impact,
        severity=report.severity,
        point=report.point,
        status=report.status,
        review_comment=report.review_comment,
        reject_reason=report.reject_reason,
        reviewed_at=report.reviewed_at,
        accepted_at=report.accepted_at,  
        rejected_at=report.rejected_at,  
        created_at=report.created_at,
        updated_at=report.updated_at,
        asset_name=asset.name if asset else None,
        user_name=user.full_name if user else None
    )

# GET /reviews/{id} - GET ASSIGNED REPORT DETAIL (ADMIN & SECURITY)
@router.get("/{report_id}")
async def get_assigned_report_detail(
    report_id: int,
    current_user: User = Depends(get_current_admin_or_security),
    db: Session = Depends(get_db)
):
    """
    Get detail of a report assigned to Security Team.
    - Admin: can view any assigned report
    - Security Team: only reports assigned to themselves
    - Status: Assigned, In Review, Accepted, Rejected
    """
    # 1. Cek report exists
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )
    
    # 2. 🔥 CEK AKSES
    if current_user.role_id == 1:  # Admin
        # Admin bisa lihat semua report yang sudah di-assign
        if report.assigned_to is None:
            raise HTTPException(
                status_code=400,
                detail="This report has not been assigned yet"
            )
    else:  # Security Team
        # Security Team cuma bisa lihat report yang di-assign ke dirinya
        if report.assigned_to != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="This report is not assigned to you"
            )
        
        # Security Team hanya bisa lihat report dengan status tertentu
        valid_statuses = ["Assigned", "In Review", "Accepted", "Rejected"]
        if report.status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Report status is {report.status}. Cannot view this report."
            )
    
    # 3. Ambil data tambahan
    asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
    user = db.query(User).filter(User.id == report.user_id).first()
    
    # 4. Ambil evidence
    evidences = db.query(ReportEvidence).filter(
        ReportEvidence.report_id == report_id
    ).order_by(ReportEvidence.created_at.desc()).all()
    
    evidence_list = []
    for evidence in evidences:
        presigned_url = minio_client.get_presigned_url(
            object_name=evidence.object_name,
            expiry=3600
        )
        evidence_list.append({
            "id": evidence.id,
            "file_name": evidence.file_name,
            "file_size": evidence.file_size,
            "content_type": evidence.content_type,
            "created_at": evidence.created_at,
            "url": presigned_url
        })
    
    # 5. Response
    return {
        "id": report.id,
        "user_id": report.user_id,
        "user_name": user.full_name if user else None,
        "asset_id": report.asset_id,
        "asset_name": asset.name if asset else None,
        "title": report.title,
        "category": report.category,
        "description": report.description,
        "steps_to_reproduce": report.steps_to_reproduce,
        "steps_to_resolve": report.steps_to_resolve,
        "impact": report.impact,
        "severity": report.severity,
        "point": report.point,
        "status": report.status,
        "review_comment": report.review_comment,
        "reject_reason": report.reject_reason,
        "reviewed_at": report.reviewed_at,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
        "evidences": evidence_list
    }