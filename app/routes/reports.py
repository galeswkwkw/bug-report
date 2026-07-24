from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status, UploadFile, File, Form  
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import uuid
import os
from typing import List

from app.database import SessionLocal
from app.models import Report, Asset, User, PointRule, ReportEvidence
from app.schemas import (
    ReportCreateRequest, ReportResponse, ReportEvidenceResponse, 
    ReportUpdateRequest, ReviewRequest, MultipleUploadResponse
)
from app.auth import get_current_active_user, get_current_admin
from app.auth import get_current_active_user
from app.minio_client import minio_client
from app.config import Config
from app.services.notification_service import NotificationService
from app.schemas import AssignReportRequest
from app.schemas import ReportUpdateByResearcherRequest

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
        
        can_edit = (report.status == "Submitted" and report.user_id == current_user.id)
        
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
            affected_endpoint=report.affected_endpoint,
            severity=report.severity,
            point=report.point,
            status=report.status,
            review_comment=report.review_comment,
            reject_reason=report.reject_reason,
            assignment_comment=report.assignment_comment,
            reviewed_at=report.reviewed_at,
            accepted_at=report.accepted_at,
            rejected_at=report.rejected_at,
            created_at=report.created_at,
            updated_at=report.updated_at,
            asset_name=asset.name if asset else None,
            user_name=user.full_name if user else None,
            can_edit=can_edit  # 
        ))
    
    return result

# GET /reports/export - EXPORT REPORTS (ADMIN ONLY)
@router.get("/export")
async def export_reports(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    format: str = "xlsx"
):
    """
    Export reports based on filters.
    - Admin only
    - Supported formats: xlsx, csv
    - Filters: status, severity, search
    """
    import io
    import csv
    from openpyxl import Workbook
    from fastapi.responses import StreamingResponse
    
    # 1. Build query
    query = db.query(Report)
    
    # 2. Apply filters
    if status:
        if status == "valid":
            query = query.filter(Report.status == "Accepted")
        elif status == "invalid":
            query = query.filter(Report.status == "Rejected")
        elif status == "in_review":
            query = query.filter(Report.status == "In Review")
        elif status == "assigned":
            query = query.filter(Report.status == "Assigned")
        elif status == "submitted":
            query = query.filter(Report.status == "Submitted")
        else:
            query = query.filter(Report.status == status)
    
    if severity:
        query = query.filter(Report.severity.ilike(f"%{severity}%"))
    
    if search:
        query = query.filter(
            (Report.title.ilike(f"%{search}%")) |
            (Report.description.ilike(f"%{search}%"))
        )
    
    # 3. Get data
    reports = query.order_by(Report.created_at.desc()).all()
    
    # 4. Build data rows
    data = []
    for report in reports:
        user = db.query(User).filter(User.id == report.user_id).first()
        asset = db.query(Asset).filter(Asset.id == report.asset_id).first()
        reviewer = db.query(User).filter(User.id == report.reviewer_id).first()
        assigned_to = db.query(User).filter(User.id == report.assigned_to).first()
        
        data.append({
            "Report ID": report.id,
            "Title": report.title,
            "Researcher Name": user.full_name if user else None,
            "Asset": asset.name if asset else None,
            "Category": report.category,
            "Severity": report.severity,
            "Status": report.status,
            "Assigned To": assigned_to.full_name if assigned_to else None,
            "Submitted At": report.created_at.strftime("%Y-%m-%d %H:%M:%S") if report.created_at else None,
            "Reviewed At": report.reviewed_at.strftime("%Y-%m-%d %H:%M:%S") if report.reviewed_at else None,
        })
    
    # 5. Generate filename
    filename = f"reports_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 6. Export berdasarkan format
    if format.lower() == "csv":
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        else:
            output.write("No data found")
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
        )
    
    else:  # default xlsx
        wb = Workbook()
        ws = wb.active
        ws.title = "Reports"
        
        if data:
            # Headers
            headers = list(data[0].keys())
            ws.append(headers)
            
            # Data rows
            for row in data:
                ws.append(list(row.values()))
        
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
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
@router.put("/{report_id}/assign")
async def assign_report(
    report_id: int,
    request: AssignReportRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Assign report to a Security Team member (Admin only).
    Request: { "security_team_id": 15, "comment": "Please review this urgently" }
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot assign report with status: {report.status}"
        )
    
    security_team = db.query(User).filter(
        User.id == request.security_team_id,
        User.role_id == 2
    ).first()
    
    if not security_team:
        raise HTTPException(
            status_code=404,
            detail=f"Security Team member with ID {request.security_team_id} not found"
        )
    
    report.assigned_to = request.security_team_id
    report.status = "Assigned"
    report.assignment_comment = request.comment  
    report.updated_at = datetime.now()
    
    db.commit()
    db.refresh(report)
    
    NotificationService.create_assignment_notification(
        db=db,
        security_id=request.security_team_id,
        report_id=report.id,
        report_title=report.title
    )
    
    return {
        "success": True,
        "message": f"Report {report_id} assigned to {security_team.full_name}",
        "report_id": report.id,
        "assigned_to": request.security_team_id,
        "assigned_to_name": security_team.full_name,
        "comment": request.comment,  
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
    
    #
    can_edit = (report.status == "Submitted" and report.user_id == current_user.id)
    
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
        affected_endpoint=report.affected_endpoint,
        impact=report.impact,
        severity=report.severity,
        point=report.point,
        status=report.status,
        review_comment=report.review_comment,
        reject_reason=report.reject_reason,
        assignment_comment=report.assignment_comment,
        reviewed_at=report.reviewed_at,
        accepted_at=report.accepted_at,
        rejected_at=report.rejected_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
        asset_name=asset.name if asset else None,
        user_name=user.full_name if user else None,
        can_edit=can_edit  
    )

# PUT /reports/evidence/{id} - UPDATE EVIDENCE (ADMIN OR OWNER)
@router.put("/evidence/{evidence_id}", response_model=ReportEvidenceResponse)
async def update_evidence(
    evidence_id: int,
    file: UploadFile = File(...),
    type: str = Form(...),  
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update evidence/result file by ID.
    - Admin: can update any evidence
    - Researcher: only their own evidence (report owner)
    - ONLY allowed if report status is 'Submitted'
    
    **type:** 'evidence' atau 'result' (wajib)
    """
    
    
    if type not in ["evidence", "result"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid type. Must be 'evidence' or 'result'"
        )
    
    
    evidence = db.query(ReportEvidence).filter(ReportEvidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence with ID {evidence_id} not found"
        )
    
    
    report = db.query(Report).filter(Report.id == evidence.report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {evidence.report_id} not found"
        )
    
    
    is_admin = current_user.role_id == 1
    is_owner = report.user_id == current_user.id
    
    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update this evidence"
        )
    
    
    if report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update evidence for report with status: {report.status}. Only Submitted reports can update evidence."
        )
    
    
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty!")
    
    max_file_size = getattr(Config, 'MAX_FILE_SIZE', 250 * 1024 * 1024)
    if file_size > max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {max_file_size / (1024*1024):.0f}MB. Your file: {file_size / (1024*1024):.2f}MB"
        )
    
    
    if type == "evidence":
        allowed_extensions = getattr(Config, 'ALLOWED_EVIDENCE_EXTENSIONS', [".pdf", ".csv", ".jpg", ".png", ".mp4", ".tar.gz"])
    else:
        allowed_extensions = getattr(Config, 'ALLOWED_RESULT_EXTENSIONS', [".pdf", ".csv", ".jpg", ".png", ".mp4", ".tar.gz"])
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File format not allowed. Allowed: {', '.join(allowed_extensions)}"
        )
    
    
    try:
        minio_client.client.remove_object(
            evidence.bucket_name,
            evidence.object_name
        )
        print(f"✅ Deleted old file from MinIO: {evidence.object_name}")
    except Exception as e:
        print(f"⚠️ Failed to delete old file: {str(e)}")
    
    
    file_extension = os.path.splitext(file.filename)[1]
    if type == "result":
        object_name = f"report_results/{evidence.report_id}/{uuid.uuid4().hex[:8]}{file_extension}"
    else:
        object_name = f"report_evidences/{evidence.report_id}/{uuid.uuid4().hex[:8]}{file_extension}"
    
    
    try:
        minio_client.upload_file(
            object_name=object_name,
            file_content=file_content,
            content_type=file.content_type
        )
        
        
        evidence.file_name = file.filename
        evidence.object_name = object_name
        evidence.bucket_name = "uploads"
        evidence.file_size = file_size
        evidence.content_type = file.content_type or "application/octet-stream"
        evidence.type = type  # 
        
        db.commit()
        db.refresh(evidence)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update evidence: {str(e)}"
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
        type=evidence.type,  
        created_at=evidence.created_at,
        url=presigned_url
    )

# PUT /reports/{id} - EDIT REPORT BY RESEARCHER (HANYA JIKA SUBMITTED)
@router.put("/{report_id}")
async def update_report_by_researcher(
    report_id: int,
    request: ReportUpdateByResearcherRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Edit report by Researcher.
    Only reports with status 'Submitted' can be edited.
    Only the owner of the report can edit it.
    """
    
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )
    
    if report.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to edit this report"
        )
    
    if report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail="This report can no longer be edited because it is already under review."
        )
    
    if request.title is not None:
        report.title = request.title
    if request.category is not None:
        report.category = request.category
    if request.description is not None:
        report.description = request.description
    if request.steps_to_reproduce is not None:
        report.steps_to_reproduce = request.steps_to_reproduce
    if request.steps_to_resolve is not None:
        report.steps_to_resolve = request.steps_to_resolve
    if request.impact is not None:
        report.impact = request.impact
    if request.affected_endpoint is not None:  
        report.affected_endpoint = request.affected_endpoint    
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
    
    return {
        "success": True,
        "message": "Report updated successfully.",
        "report_id": report.id,
        "updated_at": report.updated_at,
        "affected_endpoint": report.affected_endpoint  
    }

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
        affected_endpoint=report.affected_endpoint,
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
    
# DELETE /reports/evidence/{id} - DELETE EVIDENCE
@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete evidence by ID.
    - Admin: can delete any evidence regardless of report status
    - Researcher: only their own evidence, and only if report status is 'Submitted'
    Also deletes the file from MinIO.
    """
    
    evidence = db.query(ReportEvidence).filter(ReportEvidence.id == evidence_id).first()
    if not evidence:
        raise HTTPException(
            status_code=404,
            detail=f"Evidence with ID {evidence_id} not found"
        )
    
    
    report = db.query(Report).filter(Report.id == evidence.report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {evidence.report_id} not found"
        )
    
    
    is_admin = current_user.role_id == 1
    is_owner = report.user_id == current_user.id
    
    if not is_admin and not is_owner:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to delete this evidence"
        )
    
    
    if not is_admin and report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete evidence for report with status: {report.status}. Only Submitted reports can delete evidence."
        )
    
    
    try:
        minio_client.client.remove_object(
            evidence.bucket_name,
            evidence.object_name
        )
        print(f"✅ Deleted from MinIO: {evidence.object_name}")
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

# GET /reports/{id}/evidences - GET ALL EVIDENCES (WITH FILTER TYPE)
@router.get("/{report_id}/evidences", response_model=dict)
async def get_report_evidences(
    report_id: int,
    type: Optional[str] = None,  
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all evidences for a report.
    - Researcher: only their own reports
    - Admin/Security: all reports
    
    **Filter by type:**
    - type=evidence → hanya evidence
    - type=result → hanya result
    - type=None → semua (default)
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
    
    query = db.query(ReportEvidence).filter(ReportEvidence.report_id == report_id)
    
    if type:
        if type not in ["evidence", "result"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid type. Must be 'evidence' or 'result'"
            )
        query = query.filter(ReportEvidence.type == type)
    
    evidences = query.order_by(ReportEvidence.created_at.desc()).all()
    
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
                type=evidence.type,  # 
                created_at=evidence.created_at,
                url=presigned_url
            )
        )
    
    return {
        "success": True,
        "total": len(result),
        "data": result
    }


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
    
    asset = db.query(Asset).filter(Asset.id == request.asset_id).first()
    if not asset:
        raise HTTPException(
            status_code=404,
            detail=f"Asset with ID {request.asset_id} not found"
        )
    
    severity = None  
    
    
    point = 0
    
    
    new_report = Report(
        user_id=current_user.id,
        asset_id=request.asset_id,
        title=request.title,
        category=request.category,
        description=request.description,
        steps_to_reproduce=request.steps_to_reproduce,
        steps_to_resolve=request.steps_to_resolve,
        impact=request.impact,
        affected_endpoint=request.affected_endpoint,
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
    
    
    admin = db.query(User).filter(User.role_id == 1).first()
    if admin:
        NotificationService.create_report_notification(
            db=db,
            admin_id=admin.id,
            report_id=new_report.id,
            report_title=new_report.title
        )
    
    
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
        affected_endpoint=new_report.affected_endpoint,
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

# POST /reports/{id}/evidence - UPLOAD MULTIPLE EVIDENCE/RESULT
@router.post("/{report_id}/evidence", response_model=MultipleUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    report_id: int,
    files: List[UploadFile] = File(..., description="Upload up to 4 files (max 250MB total)"),
    type: str = Form("evidence"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Upload multiple evidence/result files for a report (User must be authenticated)
    
    - type: 'evidence' (default) atau 'result'
    - Max 4 files per upload
    - Allowed formats: PDF, CSV, JPG, PNG, MP4, TAR.GZ
    - Max per file: 250MB
    - Total max: 250MB
    
    **KEY UNTUK FILE: 'file' (bukan 'files')**
    """
    
    if type not in ["evidence", "result"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type. Must be 'evidence' or 'result'"
        )
    
    
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    max_files = getattr(Config, 'MAX_FILES_PER_UPLOAD', 4)
    if len(files) > max_files:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_files} files allowed. You uploaded {len(files)} files"
        )
    
    
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"Report with ID {report_id} not found"
        )
    
    
    if report.user_id != current_user.id and current_user.role_id != 1:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to upload evidence for this report"
        )
    
    
    if report.status != "Submitted":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot upload evidence for report with status: {report.status}"
        )
    
    
    if type == "evidence":
        allowed_extensions = getattr(Config, 'ALLOWED_EVIDENCE_EXTENSIONS', [".pdf", ".csv", ".jpg", ".png", ".mp4", ".tar.gz"])
    else:  # result
        allowed_extensions = getattr(Config, 'ALLOWED_RESULT_EXTENSIONS', [".pdf", ".csv", ".jpg", ".png", ".mp4", ".tar.gz"])
    
    max_file_size = getattr(Config, 'MAX_FILE_SIZE', 250 * 1024 * 1024)
    
    
    total_size = 0
    validated_files = []
    errors = []
    
    for idx, file in enumerate(files):
        
        if not file.filename:
            errors.append({
                "index": idx,
                "error": "File has no filename"
            })
            continue
        
        
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in allowed_extensions:
            errors.append({
                "index": idx,
                "filename": file.filename,
                "error": f"File format not allowed. Allowed: {', '.join(allowed_extensions)}"
            })
            continue
        
        
        try:
            file_content = await file.read()
        except Exception as e:
            errors.append({
                "index": idx,
                "filename": file.filename,
                "error": f"Failed to read file: {str(e)}"
            })
            continue
        
        file_size = len(file_content)
        
        if file_size == 0:
            errors.append({
                "index": idx,
                "filename": file.filename,
                "error": "File is empty!"
            })
            continue
        
        
        if file_size > max_file_size:
            errors.append({
                "index": idx,
                "filename": file.filename,
                "error": f"File too large. Max {max_file_size / (1024*1024):.0f}MB per file. Your file: {file_size / (1024*1024):.2f}MB"
            })
            continue
        
        total_size += file_size
        validated_files.append({
            "index": idx,
            "file": file,
            "filename": file.filename,
            "content": file_content,
            "size": file_size,
            "extension": ext,
            "content_type": file.content_type or "application/octet-stream"
        })
    
    
    if total_size > max_file_size:
        raise HTTPException(
            status_code=400,
            detail=f"Total files size exceeds {max_file_size / (1024*1024):.0f}MB. Current total: {total_size / (1024*1024):.2f}MB"
        )
    
    
    if errors:
        return MultipleUploadResponse(
            success=False,
            message=f"{len(errors)} file(s) failed validation",
            total_uploaded=0,
            files=[],
            errors=errors
        )
    
    
    uploaded_files = []
    upload_errors = []
    
    for file_data in validated_files:
        try:
            
            file_extension = file_data["extension"]
            if type == "result":
                object_name = f"report_results/{report_id}/{uuid.uuid4().hex[:8]}{file_extension}"
            else:
                object_name = f"report_evidences/{report_id}/{uuid.uuid4().hex[:8]}{file_extension}"
            
            
            minio_client.upload_file(
                object_name=object_name,
                file_content=file_data["content"],
                content_type=file_data["content_type"]
            )
            
            
            evidence = ReportEvidence(
                report_id=report_id,
                file_name=file_data["filename"],
                object_name=object_name,
                bucket_name="uploads",
                file_size=file_data["size"],
                content_type=file_data["content_type"],
                type=type
            )
            
            db.add(evidence)
            db.commit()
            db.refresh(evidence)
            
            
            presigned_url = minio_client.get_presigned_url(
                object_name=object_name,
                expiry=3600
            )
            
            # Prepare response
            uploaded_files.append(ReportEvidenceResponse(
                id=evidence.id,
                report_id=evidence.report_id,
                file_name=evidence.file_name,
                object_name=evidence.object_name,
                bucket_name=evidence.bucket_name,
                file_size=evidence.file_size,
                content_type=evidence.content_type,
                type=evidence.type,
                created_at=evidence.created_at,
                url=presigned_url
            ))
            
        except Exception as e:
            db.rollback()
            upload_errors.append({
                "filename": file_data["filename"],
                "error": str(e)
            })
    
    
    return MultipleUploadResponse(
        success=len(upload_errors) == 0,
        message=f"Successfully uploaded {len(uploaded_files)} {type} file(s)" if len(upload_errors) == 0 else f"Uploaded {len(uploaded_files)} file(s), {len(upload_errors)} failed",
        total_uploaded=len(uploaded_files),
        files=uploaded_files,
        errors=upload_errors if upload_errors else None
    )




