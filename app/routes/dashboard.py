from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Report, User
from app.auth import get_current_security, get_current_admin, get_current_active_user  

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# GET /dashboard/researcher - DASHBOARD RESEARCHER
async def get_researcher_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for Researcher.
    - total_report: Total reports submitted by this researcher
    - accepted: Total reports with status 'Accepted'
    - rejected: Total reports with status 'Rejected'
    - point: Total points earned by this researcher
    - rank: Ranking of this researcher (based on total_point)
    """
    total_report = db.query(Report).filter(Report.user_id == current_user.id).count()
    
    accepted = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.status == "Accepted"
    ).count()
    
    rejected = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.status == "Rejected"
    ).count()
    
    point = current_user.total_point
    
    higher_rank = db.query(User).filter(User.total_point > current_user.total_point).count()
    rank = higher_rank + 1
    
    return {
        "success": True,
        "data": {
            "total_report": total_report,
            "accepted": accepted,
            "rejected": rejected,
            "point": point,
            "rank": rank
        }
    }

# GET /dashboard/security - DASHBOARD SECURITY TEAM
@router.get("/security")
async def get_security_dashboard(
    current_user: User = Depends(get_current_security),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for Security Team.
    """
    
    assigned_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "Assigned"
    ).count()
    
    
    in_review_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "In Review"
    ).count()
    
    
    reviewed_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status.in_(["Accepted", "Rejected"])
    ).count()
    
    
    valid_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "Accepted"
    ).count()
    
    
    invalid_count = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status == "Rejected"
    ).count()
    
    
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



# GET /dashboard/admin - DASHBOARD ADMIN

@router.get("/admin")
async def get_admin_dashboard(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for Admin.
    """
    
    total_users = db.query(User).count()
    pending_users = db.query(User).filter(User.status == "Pending").count()
    active_users = db.query(User).filter(User.status == "Active").count()
    rejected_users = db.query(User).filter(User.status == "Rejected").count()
    
    
    total_reports = db.query(Report).count()
    submitted_reports = db.query(Report).filter(Report.status == "Submitted").count()
    assigned_reports = db.query(Report).filter(Report.status == "Assigned").count()
    in_review_reports = db.query(Report).filter(Report.status == "In Review").count()
    accepted_reports = db.query(Report).filter(Report.status == "Accepted").count()
    rejected_reports = db.query(Report).filter(Report.status == "Rejected").count()
    
    
    total_security = db.query(User).filter(User.role_id == 2).count()
    
    return {
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "pending": pending_users,
                "active": active_users,
                "rejected": rejected_users
            },
            "reports": {
                "total": total_reports,
                "submitted": submitted_reports,
                "assigned": assigned_reports,
                "in_review": in_review_reports,
                "accepted": accepted_reports,
                "rejected": rejected_reports
            },
            "security_team": {
                "total": total_security
            }
        }
    }