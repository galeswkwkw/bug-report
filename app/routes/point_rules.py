from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import SessionLocal
from app.models import PointRule, Role  
from app.auth import get_current_admin, get_current_user
from app.models.user import User

router = APIRouter(prefix="/point-rules", tags=["Point Rules"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET /point-rules - GET ALL POINT RULES (SEMUA USER)
@router.get("")
@router.get("/")
async def get_point_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all point rules.
    
    🔒 Authorization:
    - Admin: dapat semua field (severity, point, description, is_active, id)
    - Security Team: dapat semua field (sama seperti admin)
    - Bug Hunter: hanya severity, point, description
    """
    
   
    point_rules = db.query(PointRule).order_by(PointRule.point.desc()).all()
    
    
    role_name = None
    if current_user.role_id in [1, 2]: 
        role_name = "admin_or_security"
    elif current_user.role_id == 3:
        role_name = "bug_hunter"
    
    
    if role_name == "admin_or_security":
       
        data = [
            {
                "id": rule.id,
                "severity": rule.severity,
                "point": rule.point,
                "description": rule.description if hasattr(rule, 'description') else None,
                "is_active": rule.is_active
            }
            for rule in point_rules
        ]
    else:
       
        data = [
            {
                "severity": rule.severity,
                "point": rule.point,
                "description": rule.description if hasattr(rule, 'description') else None
                "is_active": rule.is_active
            }
            for rule in point_rules
        ]
    
    return {
        "success": True,
        "data": data
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
            "description": point_rule.description if hasattr(point_rule, 'description') else None,
            "is_active": point_rule.is_active 
        }
    }

# PUT /point-rules/{id}/toggle - TOGGLE ACTIVE STATUS
@router.put("/{rule_id}/toggle")
async def toggle_point_rule_status(
    rule_id: int,
    request: dict,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Toggle point rule active status (Admin only).
    """
    point_rule = db.query(PointRule).filter(PointRule.id == rule_id).first()
    if not point_rule:
        raise HTTPException(
            status_code=404,
            detail=f"Point rule with ID {rule_id} not found"
        )
    
    
    is_active = request.get("is_active")
    
    if is_active is None:
        
        is_active = not point_rule.is_active
    
    
    if not isinstance(is_active, bool):
        raise HTTPException(
            status_code=400,
            detail="is_active must be a boolean (true/false)"
        )
    
    point_rule.is_active = is_active
    
    db.commit()
    db.refresh(point_rule)
    
    status_text = "activated" if is_active else "deactivated"
    
    return {
        "success": True,
        "message": f"Point rule '{point_rule.severity}' has been {status_text}",
        "data": {
            "id": point_rule.id,
            "severity": point_rule.severity,
            "point": point_rule.point,
            "is_active": point_rule.is_active,
            "description": point_rule.description if hasattr(point_rule, 'description') else None
        }
    }