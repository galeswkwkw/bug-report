from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid
import os

from app.database import SessionLocal
from app.models import Report, Asset, User, PointRule, ReportEvidence
from app.schemas import ReportCreateRequest, ReportResponse, ReportEvidenceResponse, ReportUpdateRequest, ReviewRequest
from app.auth import get_current_active_user, get_current_admin
from app.auth import get_current_active_user
from app.minio_client import minio_client
from app.config import Config

router = APIRouter(prefix="/reports", tags=["Reports"])

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
    if current_user.role_id not in [1, 2]:  # Admin atau Security Team
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Security Team access required"
        )
    return current_user

# GET /reports - GET ALL REPORTS
@router.get("", response_model=list[ReportResponse])
async def get_reports(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all reports (User must be authenticated)
    """
    if current_user.role_id == 1:  
        reports = db.query(Report).order_by(Report.created_at.desc()).all()
    else:
        reports = db.query(Report).filter(Report.user_id == current_user.id).order_by(Report.created_at.desc()).all()
    
    result = []
    for report in reports:
        asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
        user = db.query(User).filter(User.id == report.user_id).first()
        
      
        reviewer_data = None
        if report.reviewer_id:
            reviewer = db.query(User).filter(User.id == report.reviewer_id).first()
            if reviewer:
                reviewer_data = {
                    "id": reviewer.id,
                    "name": reviewer.full_name
                }
        
        result.append(ReportResponse(
            id=report.id,
            user_id=report.user_id,
            asset_id=report.asset_id,
            reviewer_id=report.reviewer_id,
            reviewer=reviewer_data, 
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
            accepted_at=report.accepted_at,
            rejected_at=report.rejected_at,
            reviewed_at=report.reviewed_at,
            created_at=report.created_at,
            updated_at=report.updated_at,
            asset_name=asset.name if asset else None,
            user_name=user.full_name if user else None
        ))
    
    return result

# # 4. GET /my-assigned - GET ASSIGNED REPORTS
# # ============================================================
# @router.get("/my-assigned")
# async def get_my_assigned_reviews(
#     current_user: User = Depends(get_current_admin_or_security),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all reports assigned to current user (Security Team) or all assigned reports (Admin).
#     - Security Team: hanya report yang di-assign ke dirinya sendiri
#     - Admin: semua report yang statusnya 'Assigned'
#     """
#     if current_user.role_id == 1:  # Admin
#         reports = db.query(Report).filter(
#             Report.status == "Assigned"
#         ).order_by(Report.created_at.desc()).all()
#     else:
#         reports = db.query(Report).filter(
#             Report.assigned_to == current_user.id,
#             Report.status == "Assigned"
#         ).order_by(Report.created_at.desc()).all()
    
#     result = []
#     for report in reports:
#         asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
#         user = db.query(User).filter(User.id == report.user_id).first()
        
#         result.append({
#             "id": report.id,
#             "title": report.title,
#             "asset": asset.domain if asset else None,
#             "asset_name": asset.name if asset else None,
#             "reporter": user.full_name if user else None,
#             "severity": report.severity,
#             "status": report.status,
#             "created_at": report.created_at,
#             "updated_at": report.updated_at
#         })
    
#     return {
#         "success": True,
#         "count": len(result),
#         "data": result
#     }


# # GET /reports/review - GET PENDING REPORTS (SECURITY TEAM ONLY)
# @router.get("/review")
# async def get_review_reports(
#     current_user: User = Depends(get_current_security), 
#     db: Session = Depends(get_db)
# ):
#     """
#     Get all pending reports (status = Submitted) for Security Team review.
#     """
#     reports = db.query(Report).filter(Report.status == "Submitted").order_by(Report.created_at.desc()).all()
    
#     result = []
#     for report in reports:
#         asset = db.query(Asset).filter(Asset.id == report.asset_id).first()

#         user = db.query(User).filter(User.id == report.user_id).first()
        
#         result.append({
#             "id": report.id,
#             "user_id": report.user_id,
#             "user_name": user.full_name if user else None,
#             "asset_id": report.asset_id,
#             "asset_name": asset.name if asset else None,
#             "title": report.title,
#             "category": report.category,
#             "description": report.description,
#             "steps_to_reproduce": report.steps_to_reproduce,
#             "steps_to_resolve": report.steps_to_resolve,
#             "impact": report.impact,
#             "severity": report.severity,
#             "point": report.point,
#             "status": report.status,
#             "created_at": report.created_at,
#             "updated_at": report.updated_at
#         })
    
#     return {
#         "success": True,
#         "count": len(result),
#         "data": result
#     }


# # PUT /review/reports/{id} - REVIEW REPORT (SECURITY TEAM ONLY)
# @router.put("/review/{report_id}", response_model=ReportResponse)
# async def review_report(
#     report_id: int,
#     request: ReviewRequest,
#     current_user: User = Depends(get_current_security),  
#     db: Session = Depends(get_db)
# ):
#     """
#     Review report by Security Team.
#     - Accept: set severity, comment → point otomatis dihitung
#     - Reject: set reject_reason, comment → point tetap 0
#     """
#     report = db.query(Report).filter(Report.id == report_id).first()
#     if not report:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Report with ID {report_id} not found"
#         )
    
#     if report.status != "Submitted":
#         raise HTTPException(
#             status_code=400,
#             detail=f"Cannot review report with status: {report.status}. Only Submitted reports can be reviewed."
#         )
    
#     if request.result not in ["accepted", "rejected"]:
#         raise HTTPException(
#             status_code=400,
#             detail="Result must be 'accepted' or 'rejected'"
#         )
    
#     if request.result == "accepted":
#         if not request.severity:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Severity is required when accepting a report"
#             )
        
#         valid_severities = ["Critical", "High", "Medium", "Low", "Informational"]
#         if request.severity not in valid_severities:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Invalid severity. Must be one of: {', '.join(valid_severities)}"
#             )
        
#         report.status = "Accepted"
#         report.severity = request.severity
#         report.review_comment = request.comment
#         report.reviewer_id = current_user.id
#         report.reviewed_at = datetime.now()
        
#         point_rule = db.query(PointRule).filter(PointRule.severity == request.severity).first()
#         report.point = point_rule.point if point_rule else 0
        
#         user = db.query(User).filter(User.id == report.user_id).first()
#         if user:
#             user.total_point += report.point
#             db.add(user)
    
#     elif request.result == "rejected":
#         if not request.reject_reason:
#             raise HTTPException(
#                 status_code=400,
#                 detail="Reject reason is required when rejecting a report"
#             )
        
#         report.status = "Rejected"
#         report.reject_reason = request.reject_reason
#         report.review_comment = request.comment
#         report.reviewer_id = current_user.id
#         report.reviewed_at = datetime.now()
#         report.point = 0  
    
#     # Update timestamp
#     report.updated_at = datetime.now()
    
#     try:
#         db.commit()
#         db.refresh(report)
#     except IntegrityError as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=400,
#             detail=f"Failed to review report: {str(e)}"
#         )
    
#     asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
#     user = db.query(User).filter(User.id == report.user_id).first()
    
#     return ReportResponse(
#         id=report.id,
#         user_id=report.user_id,
#         asset_id=report.asset_id,
#         reviewer_id=report.reviewer_id,
#         title=report.title,
#         category=report.category,
#         description=report.description,
#         steps_to_reproduce=report.steps_to_reproduce,
#         steps_to_resolve=report.steps_to_resolve,
#         impact=report.impact,
#         severity=report.severity,
#         point=report.point,
#         status=report.status,
#         review_comment=report.review_comment,
#         reject_reason=report.reject_reason,
#         reviewed_at=report.reviewed_at,
#         created_at=report.created_at,
#         updated_at=report.updated_at,
#         asset_name=asset.name if asset else None,
#         user_name=user.full_name if user else None
#     )

# # GET /reports/review/{id} - GET PENDING REPORT DETAIL (SECURITY TEAM ONLY)
# @router.get("/review/{report_id}")
# async def get_review_report_detail(
#     report_id: int,
#     current_user: User = Depends(get_current_security), 
#     db: Session = Depends(get_db)
# ):
#     """
#     Get detail of a pending report (status = Submitted) for Security Team review.
#     """
#     report = db.query(Report).filter(Report.id == report_id).first()
#     if not report:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Report with ID {report_id} not found"
#         )
    
#     if report.status != "Submitted":
#         raise HTTPException(
#             status_code=400,
#             detail=f"Report status is {report.status}. Only Submitted reports can be reviewed."
#         )
    
#     asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
#     user = db.query(User).filter(User.id == report.user_id).first()
    
#     evidences = db.query(ReportEvidence).filter(
#         ReportEvidence.report_id == report_id
#     ).order_by(ReportEvidence.created_at.desc()).all()
    
#     evidence_list = []
#     for evidence in evidences:
#         presigned_url = minio_client.get_presigned_url(
#             object_name=evidence.object_name,
#             expiry=3600
#         )
#         evidence_list.append({
#             "id": evidence.id,
#             "file_name": evidence.file_name,
#             "file_size": evidence.file_size,
#             "content_type": evidence.content_type,
#             "created_at": evidence.created_at,
#             "url": presigned_url
#         })
    
#     # 5. Response
#     return {
#         "id": report.id,
#         "user_id": report.user_id,
#         "user_name": user.full_name if user else None,
#         "asset_id": report.asset_id,
#         "asset_name": asset.name if asset else None,
#         "title": report.title,
#         "category": report.category,
#         "description": report.description,
#         "steps_to_reproduce": report.steps_to_reproduce,
#         "steps_to_resolve": report.steps_to_resolve,
#         "impact": report.impact,
#         "severity": report.severity,
#         "point": report.point,
#         "status": report.status,
#         "created_at": report.created_at,
#         "updated_at": report.updated_at,
#         "evidences": evidence_list
#     }

# PUT /reports/{id}/assign - ASSIGN REPORT TO SECURITY TEAM (ADMIN ONLY)
@router.put("/{report_id}/assign")  # ← HAPUS "reports/"!
async def assign_report(
    report_id: int,
    request: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Assign report to a Security Team member (Admin only).
    Request: { "security_team_id": 15 }
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign report with status: {report.status}"
        )
    
    security_team_id = request.get("security_team_id")
    if not security_team_id:
        raise HTTPException(status_code=400, detail="security_team_id is required")
    
    security_team = db.query(User).filter(
        User.id == security_team_id,
        User.role_id == 2
    ).first()
    
    if not security_team:
        raise HTTPException(
            status_code=404,
            detail=f"Security Team member with ID {security_team_id} not found"
        )
    
    report.assigned_to = security_team_id
    report.status = "Assigned"
    report.updated_at = datetime.now()
    
    db.commit()
    db.refresh(report)
    
    return {
        "success": True,
        "message": f"Report {report_id} assigned to {security_team.full_name}",
        "report_id": report.id,
        "assigned_to": security_team_id,
        "assigned_to_name": security_team.full_name,
        "status": report.status
    }


# GET /reports/{id} - GET REPORT BY ID
@router.get("/{report_id}", response_model=ReportResponse)
async def get_report_by_id(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get report by ID (User must be authenticated)
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )
    
    if current_user.role_id != 1 and report.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this report"
        )
    
    asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
    user = db.query(User).filter(User.id == report.user_id).first()
    
    
    reviewer_data = None
    if report.reviewer_id:
        reviewer = db.query(User).filter(User.id == report.reviewer_id).first()
        if reviewer:
            reviewer_data = {
                "id": reviewer.id,
                "name": reviewer.full_name
            }
    
    return ReportResponse(
        id=report.id,
        user_id=report.user_id,
        asset_id=report.asset_id,
        reviewer_id=report.reviewer_id,
        reviewer=reviewer_data, 
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
        created_at=report.created_at,
        updated_at=report.updated_at,
        asset_name=asset.name if asset else None,
        user_name=user.full_name if user else None
    )

# PUT /reports/{id} - UPDATE REPORT STATUS (ADMIN ONLY)
@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    request: ReportUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update report status by ID (Admin only).
    Only Submitted reports can be updated.
    Admin can only change status (Accepted/Rejected).
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )
    
    if report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update report with status: {report.status}. Only Submitted reports can be updated."
        )
    
    
    if request.status is not None:
        if request.status not in ["Accepted", "Rejected"]:
            raise HTTPException(
                status_code=400,
                detail="Status must be 'Accepted' or 'Rejected'"
            )
        
        report.status = request.status
        report.reviewed_at = datetime.now()
        report.reviewer_id = current_user.id
    
    report.updated_at = datetime.now()
    
    try:
        db.commit()
        db.refresh(report)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to update report: {str(e)}"
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
        created_at=report.created_at,
        updated_at=report.updated_at,
        asset_name=asset.name if asset else None,
        user_name=user.full_name if user else None
    )

# DELETE /reports/{id} - DELETE REPORT (ADMIN ONLY)
@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete report by ID (Admin only).
    Also deletes all evidence files from MinIO.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )
    
    evidences = db.query(ReportEvidence).filter(ReportEvidence.report_id == report_id).all()
    
    for evidence in evidences:
        try:
            minio_client.client.remove_object(
                evidence.bucket_name,
                evidence.object_name
            )
            print(f"✅ Deleted from MinIO: {evidence.object_name}")
        except Exception as e:
            print(f"⚠️ Failed to delete {evidence.object_name}: {str(e)}")
    
    db.delete(report)
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete report: {str(e)}"
        )
    
    return None  # 204 No Content

# DELETE /reports/evidence/{id} - DELETE EVIDENCE (ADMIN ONLY)
@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_admin),  
    db: Session = Depends(get_db)
):
    """
    Delete evidence by ID (Admin only).
    Also deletes the file from MinIO.
    """
    evidence = db.query(ReportEvidence).filter(ReportEvidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence with ID {evidence_id} not found"
        )
    
    try:
        minio_client.client.remove_object(
            evidence.bucket_name,
            evidence.object_name
        )
    except Exception as e:
        print(f"⚠️ Failed to delete file from MinIO: {str(e)}")
    
    db.delete(evidence)
    
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to delete evidence: {str(e)}"
        )
    
    return None  # 204 No Content

# GET /reports/{id}/evidences - GET ALL EVIDENCES
@router.get("/{report_id}/evidences", response_model=list[ReportEvidenceResponse])
async def get_report_evidences(
    report_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all evidences for a report.
    - Researcher: only their own reports
    - Admin/Security: all reports
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )

    is_admin_or_security = current_user.role_id in [1, 3]  
    if not is_admin_or_security and report.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view evidences for this report"
        )
    
    evidences = db.query(ReportEvidence).filter(
        ReportEvidence.report_id == report_id
    ).order_by(ReportEvidence.created_at.desc()).all()
    
    result = []
    for evidence in evidences:
        presigned_url = minio_client.get_presigned_url(
            object_name=evidence.object_name,
            expiry=3600
        )
        result.append(
            ReportEvidenceResponse(
                id=evidence.id,
                report_id=evidence.report_id,
                file_name=evidence.file_name,
                object_name=evidence.object_name,
                bucket_name=evidence.bucket_name,
                file_size=evidence.file_size,
                content_type=evidence.content_type,
                created_at=evidence.created_at,
                url=presigned_url
            )
        )
    
    return result

# POST /reports - CREATE REPORT
@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    request: ReportCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new vulnerability report (User must be authenticated)
    """
    # 1. Cek asset exists
    asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset with ID {request.asset_id} not found"
        )
    
    # 2. 🔥 HANDLE SEVERITY OPSIONAL
    if request.severity is None or request.severity == "":
        severity = "Low"
    else:
        severity = request.severity
    
    # 3. Validasi severity (kalau diisi)
    valid_severities = ["Critical", "High", "Medium", "Low", "Informational"]
    if severity not in valid_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severity. Must be one of: {', '.join(valid_severities)}"
        )
    
    # 4. POINT = 0 (nanti dikasih IT Security)
    point = 0
    
    # 5. Buat report
    new_report = Report(
        user_id=current_user.id,
        asset_id=request.asset_id,
        title=request.title,
        category=request.category,
        description=request.description,
        steps_to_reproduce=request.steps_to_reproduce,
        steps_to_resolve=request.steps_to_resolve,
        impact=request.impact,
        severity=severity,
        point=point,
        status="Submitted"
    )
    
    db.add(new_report)
    
    try:
        db.commit()
        db.refresh(new_report)
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Failed to create report: {str(e)}"
        )
    
    # 6. Response
    return ReportResponse(
        id=new_report.id,
        user_id=new_report.user_id,
        asset_id=new_report.asset_id,
        reviewer_id=new_report.reviewer_id,
        title=new_report.title,
        category=new_report.category,
        description=new_report.description,
        steps_to_reproduce=new_report.steps_to_reproduce,
        steps_to_resolve=new_report.steps_to_resolve,
        impact=new_report.impact,
        severity=new_report.severity,
        point=new_report.point,
        status=new_report.status,
        review_comment=new_report.review_comment,
        reject_reason=new_report.reject_reason,
        reviewed_at=new_report.reviewed_at,
        created_at=new_report.created_at,
        updated_at=new_report.updated_at,
        asset_name=asset.name,
        user_name=current_user.full_name
    )


# POST /reports/{id}/evidence - UPLOAD EVIDENCE
@router.post("/{report_id}/evidence", response_model=ReportEvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    report_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload evidence file for a report (User must be authenticated)
    """
    # 1. Cek report exists
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )
    
    if report.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to upload evidence for this report"
        )
    
    if report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload evidence for report with status: {report.status}"
        )
    
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty!")
    
    if file_size > Config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: 10MB. Your file: {file_size} bytes"
        )
    
    # 5. Generate object name
    file_extension = os.path.splitext(file.filename)[1]
    object_name = f"report_evidences/{report_id}/{uuid.uuid4().hex[:8]}{file_extension}"
    
    try:
        minio_client.upload_file(
            object_name=object_name,
            file_content=file_content,
            content_type=file.content_type
        )
        
        evidence = ReportEvidence(
            report_id=report_id,
            file_name=file.filename,
            object_name=object_name,
            bucket_name="uploads",
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream"
        )
        
        db.add(evidence)
        db.commit()
        db.refresh(evidence)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload evidence: {str(e)}"
        )
    
    presigned_url = minio_client.get_presigned_url(
        object_name=object_name,
        expiry=3600
    )
    
    return ReportEvidenceResponse(
        id=evidence.id,
        report_id=evidence.report_id,
        file_name=evidence.file_name,
        object_name=evidence.object_name,
        bucket_name=evidence.bucket_name,
        file_size=evidence.file_size,
        content_type=evidence.content_type,
        created_at=evidence.created_at,
        url=presigned_url
    )





