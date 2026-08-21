from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Report, User, Asset, PointRule  
from app.auth import get_current_admin

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("")
async def get_monitoring(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get monitoring dashboard data.
    🔒 ADMIN ONLY
    """
    
  
    monthly_trend = []
    current_date = datetime.now()
    
    for i in range(5, -1, -1):
        month_date = current_date - timedelta(days=30 * i)
        month_name = month_date.strftime("%B")
        
        total_reports = db.query(Report).filter(
            extract('month', Report.created_at) == month_date.month,
            extract('year', Report.created_at) == month_date.year
        ).count()
        
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
    
  
    active_severities = db.query(PointRule.severity).filter(
        PointRule.is_active == True
    ).all()
    active_severity_list = [s[0].lower() for s in active_severities]

    severity_distribution = {}
    for severity in active_severity_list:
        severity_distribution[severity] = 0

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

   
   
   
    total_rejected = db.query(Report).filter(Report.status == "Rejected").count()

    
    return {
        "success": True,
        "data": {
            "monthly_trend": monthly_trend,
            "security_team_performance": security_team_performance,
            "top_assets": top_assets_data,
            "severity_distribution": severity_distribution,
            "rejected_reports": total_rejected 
        }
    }