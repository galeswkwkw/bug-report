from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Report, User, Asset
from app.auth import get_current_active_user, get_current_security, get_current_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/researcher")
async def get_researcher_dashboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for Researcher.
    """
    total_reports = db.query(Report).filter(Report.user_id == current_user.id).count()
    
    submitted_reports = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.status == "Submitted"
    ).count()
    
    in_review_reports = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.status == "In Review"
    ).count()
    
    reviewed_reports = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.status.in_(["Accepted", "Rejected"])
    ).count()
    
    total_points = current_user.total_point
    
    higher_rank = db.query(User).filter(
        User.role_id == 3,
        User.total_point > current_user.total_point
    ).count()
    leaderboard_rank = higher_rank + 1
    
    severity_distribution = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "informational": 0
    }
    
    severity_stats = db.query(
        Report.severity,
        func.count(Report.id).label("total")
    ).filter(
        Report.user_id == current_user.id,
        Report.status == "Accepted"
    ).group_by(Report.severity).all()
    
    total_accepted = db.query(Report).filter(
        Report.user_id == current_user.id,
        Report.status == "Accepted"
    ).count() or 1
    
    for stat in severity_stats:
        key = stat.severity.lower()
        if key in severity_distribution:
            severity_distribution[key] = stat.total
    
    severity_percentage = {}
    for key, value in severity_distribution.items():
        severity_percentage[key] = {
            "count": value,
            "percentage": round((value / total_accepted) * 100, 1) if total_accepted > 0 else 0
        }
    
    recent_reports = db.query(Report).filter(
        Report.user_id == current_user.id
    ).order_by(
        Report.created_at.desc()
    ).limit(5).all()
    
    recent_reports_data = []
    for report in recent_reports:
        status_map = {
            "Submitted": "submitted",
            "Assigned": "assigned",
            "In Review": "in_review",
            "Accepted": "accepted/valid",
            "Rejected": "rejected/invalid"
        }
        recent_reports_data.append({
            "id": report.id,
            "title": report.title,
            "severity": report.severity.lower() if report.severity else None,
            "status": status_map.get(report.status, report.status.lower()),
            "submitted": report.created_at.isoformat()
        })
    
    return {
        "success": True,
        "data": {
            "total_reports": total_reports,
            "submitted_reports": submitted_reports,
            "in_review_reports": in_review_reports,
            "reviewed_reports": reviewed_reports,
            "total_points": total_points,
            "leaderboard_rank": leaderboard_rank,
            "severity_distribution": severity_percentage,
            "recent_reports": recent_reports_data
        }
    }


@router.get("/security")
async def get_security_dashboard(
    current_user: User = Depends(get_current_security),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for Security Team.
    """
    pending_review = db.query(Report).filter(
        Report.assigned_to == current_user.id,
        Report.status.in_(["Assigned", "In Review"])
    ).count()
    
    today = datetime.now().date()
    accepted_today = db.query(Report).filter(
        Report.reviewer_id == current_user.id,
        Report.status == "Accepted",
        func.date(Report.reviewed_at) == today
    ).count()
    
    rejected_today = db.query(Report).filter(
        Report.reviewer_id == current_user.id,
        Report.status == "Rejected",
        func.date(Report.reviewed_at) == today
    ).count()
    
    return {
        "success": True,
        "data": {
            "pending_review": pending_review,
            "accepted_today": accepted_today,
            "rejected_today": rejected_today
        }
    }


@router.get("/admin")
async def get_admin_dashboard(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics for Admin.
    """
    total_users = db.query(User).count()
    total_researchers = db.query(User).filter(User.role_id == 3).count()
    total_security_teams = db.query(User).filter(User.role_id == 2).count()
    
    total_reports = db.query(Report).count()
    submitted_reports = db.query(Report).filter(Report.status == "Submitted").count()
    assigned_reports = db.query(Report).filter(Report.status == "Assigned").count()
    in_review_reports = db.query(Report).filter(Report.status == "In Review").count()
    valid_reports = db.query(Report).filter(Report.status == "Accepted").count()
    invalid_reports = db.query(Report).filter(Report.status == "Rejected").count()
    total_assets = db.query(Asset).count()
    
    severity_distribution = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "informational": 0
    }
    
    severity_stats = db.query(
        Report.severity,
        func.count(Report.id).label("total")
    ).filter(
        Report.status == "Accepted"
    ).group_by(Report.severity).all()
    
    total_accepted = valid_reports or 1
    
    for stat in severity_stats:
        key = stat.severity.lower()
        if key in severity_distribution:
            severity_distribution[key] = stat.total
    
    severity_percentage = {}
    for key, value in severity_distribution.items():
        severity_percentage[key] = {
            "count": value,
            "percentage": round((value / total_accepted) * 100, 1) if total_accepted > 0 else 0
        }
    
    recent_reports = db.query(Report).order_by(
        Report.created_at.desc()
    ).limit(5).all()
    
    recent_reports_data = []
    for report in recent_reports:
        researcher = db.query(User).filter(User.id == report.user_id).first()
        assigned_to = db.query(User).filter(User.id == report.assigned_to).first()
        
        status_map = {
            "Submitted": "submitted",
            "Assigned": "assigned",
            "In Review": "in_review",
            "Accepted": "accepted/valid",
            "Rejected": "rejected/invalid"
        }
        
        recent_reports_data.append({
            "id": report.id,
            "title": report.title,
            "researcher_name": researcher.full_name if researcher else None,
            "assigned_to": assigned_to.full_name if assigned_to else None,
            "status": status_map.get(report.status, report.status.lower()),
            "submitted": report.created_at.isoformat()
        })
    
    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "total_researchers": total_researchers,
            "total_security_teams": total_security_teams,
            "total_reports": total_reports,
            "submitted_reports": submitted_reports,
            "assigned_reports": assigned_reports,
            "in_review_reports": in_review_reports,
            "valid_reports": valid_reports,
            "invalid_reports": invalid_reports,
            "total_assets": total_assets,
            "severity_distribution": severity_percentage,
            "recent_reports": recent_reports_data
        }
    }