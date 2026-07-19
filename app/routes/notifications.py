from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import SessionLocal
from app.models import Notification, User
from app.auth import get_current_active_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# GET /notifications - GET NOTIFICATIONS

@router.get("")
async def get_notifications(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_read: bool = Query(None)
):
    """
    Get notifications for current user with pagination.
    """
    
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    
    
    total = query.count()
    
    
    notifications = query.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "page": page,
        "limit": limit,
        "total": total,
        "data": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "reference_id": n.reference_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications
        ]
    }



# GET /notifications/unread-count - GET UNREAD COUNT

@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get count of unread notifications.
    """
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {"count": count}



# PUT /notifications/{id}/read - MARK AS READ

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark a specific notification as read.
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "Notification marked as read."}



# PUT /notifications/read-all - MARK ALL AS READ

@router.put("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mark all notifications as read.
    """
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
    return {"message": "All notifications marked as read."}