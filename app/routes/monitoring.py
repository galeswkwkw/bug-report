from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Report, User, Asset
from app.auth import get_current_active_user

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# GET /monitoring - GET MONITORING DASHBOARD (ALL USERS)
# ============================================================
@router.get("")
async def get_monitoring(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get monitoring dashboard data.
    Accessible by all authenticated users.
    """
    # ============================================================
    # 1. MONTHLY TREND (6 bulan terakhir)
    # ============================================================
    monthly_trend = []
    current_date = datetime.now()
    
    for i in range(5, -1, -1):  # 6 bulan terakhir
        month_date = current_date - timedelta(days=30 * i)
        month_name = month_date.strftime("%B")
        
        # Total reports bulan ini
        total_reports = db.query(Report).filter(
            extract('month', Report.created_at) == month_date.month,
            extract('year', Report.created_at) == month_date.year
        ).count()
        
        # Valid reports (Accepted) bulan ini
        valid_reports = db.query(Report).filter(
            extract('month', Report.created_at) == month_date.month,
            extract('year', Report.created_at) == month_date.year,
            Report.status == "Accepted"
        ).count()
        
        monthly_trend.append({
            "month": month_name,
            "total_reports": total_reports,
            "valid_reports": valid_reports
        })
    
    # ============================================================
    # 2. SECURITY TEAM PERFORMANCE
    # ============================================================
    security_teams = db.query(User).filter(User.role_id == 2).all()
    
    security_team_performance = []
    for team in security_teams:
        assigned = db.query(Report).filter(Report.assigned_to == team.id).count()
        reviewed = db.query(Report).filter(
            Report.reviewer_id == team.id,
            Report.status.in_(["Accepted", "Rejected"])
        ).count()
        in_review = db.query(Report).filter(
            Report.assigned_to == team.id,
            Report.status == "In Review"
        ).count()
        
        security_team_performance.append({
            "security_team_name": team.full_name,
            "assigned_reports": assigned,
            "reviewed_reports": reviewed,
            "in_review_reports": in_review
        })
    
    # ============================================================
    # 3. TOP ASSETS (berdasarkan total reports)
    # ============================================================
    top_assets = db.query(
        Asset.id,
        Asset.name,
        func.count(Report.id).label("total_reports")
    ).join(
        Report, Report.asset_id == Asset.id
    ).group_by(
        Asset.id, Asset.name
    ).order_by(
        func.count(Report.id).desc()
    ).limit(10).all()
    
    top_assets_data = []
    for asset in top_assets:
        top_assets_data.append({
            "asset_name": asset.name,
            "total_reports": asset.total_reports
        })
    
    # ============================================================
    # 4. SEVERITY DISTRIBUTION
    # ============================================================
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
    
    for stat in severity_stats:
        key = stat.severity.lower()
        if key in severity_distribution:
            severity_distribution[key] = stat.total
    
    # ============================================================
    # RESPONSE
    # ============================================================
    return {
        "success": True,
        "data": {
            "monthly_trend": monthly_trend,
            "security_team_performance": security_team_performance,
            "top_assets": top_assets_data,
            "severity_distribution": severity_distribution
        }
    }