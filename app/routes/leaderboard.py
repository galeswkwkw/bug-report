from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import SessionLocal
from app.models import User, Report
from app.auth import get_current_active_user

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /leaderboard - GET LEADERBOARD (ALL USERS)
@router.get("")
async def get_leaderboard(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get leaderboard ranking of all researchers based on total points.
    Only shows users with role_id = 2 (Researcher).
    """
    users = db.query(User).filter(
        User.role_id == 3
    ).order_by(
        User.total_point.desc()
    ).all()
    
    result = []
    rank = 1
    for user in users:
        total_accepted = db.query(Report).filter(
            Report.user_id == user.id,
            Report.status == "Accepted"
        ).count()
        
        result.append({
            "rank": rank,
            "name": user.full_name,
            "point": user.total_point,
            "total_accepted": total_accepted
        })
        rank += 1
    
    return {
        "success": True,
        "count": len(result),
        "data": result
    }


# GET /leaderboard/top/{limit} - GET TOP N RESEARCHERS
@router.get("/top/{limit}")
async def get_top_leaderboard(
    limit: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get top N researchers based on total points.
    """
    users = db.query(User).filter(
        User.role_id == 2
    ).order_by(
        User.total_point.desc()
    ).limit(limit).all()
    
    result = []
    rank = 1
    for user in users:
        total_accepted = db.query(Report).filter(
            Report.user_id == user.id,
            Report.status == "Accepted"
        ).count()
        
        result.append({
            "rank": rank,
            "name": user.full_name,
            "point": user.total_point,
            "total_accepted": total_accepted
        })
        rank += 1
    
    return {
        "success": True,
        "count": len(result),
        "data": result
    }