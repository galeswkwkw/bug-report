from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import SessionLocal
from app.models import PointRule
from app.auth import get_current_admin, get_current_user
from app.models.user import User

router = APIRouter(prefix="/point-rules", tags=["Point Rules"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# GET /point-rules - GET ALL POINT RULES
@router.get("")
@router.get("/")
async def get_point_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all point rules (Admin & Security Team only).
    """
    # ✅ CEK ROLE: Hanya Admin atau Security Team
    role = db.query(Role).filter(Role.id == current_user.role_id).first()
    
    if role.name not in ["Admin", "Security Team"]:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Only Admin and Security Team can view point rules."
        )
    
    point_rules = db.query(PointRule).order_by(PointRule.id).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": rule.id,
                "severity": rule.severity,
                "point": rule.point,
                "description": rule.description if hasattr(rule, 'description') else None
            }
            for rule in point_rules
        ]
    }



# PUT /point-rules/{id} - UPDATE POINT RULE
@router.put("/{rule_id}")
async def update_point_rule(
    rule_id: int,
    request: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Update point rule by ID (Admin only).
    """
    point_rule = db.query(PointRule).filter(PointRule.id == rule_id).first()
    if not point_rule:
        raise HTTPException(
            status_code=404,
            detail=f"Point rule with ID {rule_id} not found"
        )
    
    point = request.get("point")
    description = request.get("description")
    
    if point is None:
        raise HTTPException(
            status_code=400,
            detail="point is required"
        )
    
    if not isinstance(point, int) or point < 0:
        raise HTTPException(
            status_code=400,
            detail="point must be a positive integer"
        )
    
    point_rule.point = point
    if description is not None:
        point_rule.description = description
    
    db.commit()
    db.refresh(point_rule)
    
    return {
        "success": True,
        "message": "Point rule updated successfully.",
        "data": {
            "id": point_rule.id,
            "severity": point_rule.severity,
            "point": point_rule.point,
            "description": point_rule.description if hasattr(point_rule, 'description') else None
        }
    }