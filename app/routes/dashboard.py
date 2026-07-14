from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Report, User
from app.auth import get_current_security, get_current_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# GET /dashboard/security - DASHBOARD SECURITY TEAM
# ============================================================
@router.get("/security")
async def get_security_dashboard(
    current_user: User = Depends(get_current_security),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for Security Team.
    """
    # 1. Assigned Reports (status = Assigned)
    assigned_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "Assigned"
    ).count()
    
    # 2. In Review (status = In Review)
    in_review_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "In Review"
    ).count()
    
    # 3. Reviewed Reports (Accepted + Rejected)
    reviewed_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status.in_(["Accepted", "Rejected"])
    ).count()
    
    # 4. Valid Reports (Accepted)
    valid_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "Accepted"
    ).count()
    
    # 5. Invalid Reports (Rejected)
    invalid_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "Rejected"
    ).count()
    
    # 6. Total Reports Assigned
    total_assigned = assigned_count + in_review_count + reviewed_count
    
    return {
        "success": True,
        "data": {
            "assigned_reports": assigned_count,
            "in_review": in_review_count,
            "reviewed_reports": reviewed_count,
            "valid_reports": valid_count,
            "invalid_reports": invalid_count,
            "total_assigned": total_assigned
        }
    }


# # ============================================================
# # GET /dashboard/admin - DASHBOARD ADMIN
# # ============================================================
# @router.get("/admin")
# async def get_admin_dashboard(
#     current_user: User = Depends(get_current_admin),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get dashboard statistics for Admin.
#     """
#     # Total users by status
#     total_users = db.query(User).count()
#     pending_users = db.query(User).filter(User.status == "Pending").count()
#     active_users = db.query(User).filter(User.status == "Active").count()
#     rejected_users = db.query(User).filter(User.status == "Rejected").count()
    
#     # Total reports by status
#     total_reports = db.query(Report).count()
#     submitted_reports = db.query(Report).filter(Report.status == "Submitted").count()
#     assigned_reports = db.query(Report).filter(Report.status == "Assigned").count()
#     in_review_reports = db.query(Report).filter(Report.status == "In Review").count()
#     accepted_reports = db.query(Report).filter(Report.status == "Accepted").count()
#     rejected_reports = db.query(Report).filter(Report.status == "Rejected").count()
    
#     # Total security team
#     total_security = db.query(User).filter(User.role_id == 2).count()
    
#     return {
#         "success": True,
#         "data": {
#             "users": {
#                 "total": total_users,
#                 "pending": pending_users,
#                 "active": active_users,
#                 "rejected": rejected_users
#             },
#             "reports": {
#                 "total": total_reports,
#                 "submitted": submitted_reports,
#                 "assigned": assigned_reports,
#                 "in_review": in_review_reports,
#                 "accepted": accepted_reports,
#                 "rejected": rejected_reports
#             },
#             "security_team": {
#                 "total": total_security
#             }
#         }
#     }