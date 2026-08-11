from sqlalchemy.orm import Session
from app.models import Notification, User, Report

class NotificationService:
    
    @staticmethod
    def create_notification(db: Session, user_id: int, title: str, message: str, type: str, reference_id: int = None):
        """Buat notifikasi untuk 1 user"""
        notification = Notification(
            user_id=user_id,
            role_id=role_id,
            title=title,
            message=message,
            type=type,
            reference_id=reference_id
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def notify_all_admins(db: Session, title: str, message: str, type: str, reference_id: int = None):
        """Kirim notifikasi ke semua user dengan role_id = 1 (Admin)"""
        admins = db.query(User).filter(User.role_id == 1).all()
        for admin in admins:
            NotificationService.create_notification(
                db=db,
                user_id=admin.id,
                role_id=1,
                title=title,
                message=message,
                type=type,
                reference_id=reference_id
            )

    @staticmethod
    def create_registration_notification(db: Session, user_name: str):
        NotificationService.notify_all_admins(
            db=db,
            title="New Registration",
            message=f"User {user_name} has registered and requires approval.",
            type="registration"
        )

    @staticmethod
    def create_report_notification(db: Session, report_id: int, report_title: str):
        NotificationService.notify_all_admins(
            db=db,
            title="New Report Submitted",
            message=f"New report '{report_title}' has been submitted for review.",
            type="report",
            reference_id=report_id
        )

    @staticmethod
    def create_assignment_notification(db: Session, security_id: int, report_id: int, report_title: str):
        return NotificationService.create_notification(
            db=db,
            user_id=security_id,
            title="Report Assigned",
            message=f"Report '{report_title}' has been assigned to you for review.",
            type="assignment",
            reference_id=report_id
        )

    @staticmethod
    def create_review_started_notification(db: Session, researcher_id: int, report_id: int, report_title: str):
        NotificationService.create_notification(
            db=db,
            user_id=researcher_id,
            title="Report Under Review",
            message=f"Your report '{report_title}' is now under review.",
            type="review_started",
            reference_id=report_id
        )
        NotificationService.notify_all_admins(
            db=db,
            title="Report Under Review",
            message=f"Report '{report_title}' is now being reviewed.",
            type="review_started",
            reference_id=report_id
        )

    @staticmethod
    def create_review_completed_notification(db: Session, researcher_id: int, report_id: int, report_title: str, status: str):
        status_text = "accepted" if status == "Accepted" else "rejected"
        NotificationService.create_notification(
            db=db,
            user_id=researcher_id,
            title=f"Report {status_text}",
            message=f"Your report '{report_title}' has been {status_text}.",
            type="review_completed",
            reference_id=report_id
        )
        NotificationService.notify_all_admins(
            db=db,
            title=f"Report {status_text}",
            message=f"Report '{report_title}' has been {status_text} by Security Team.",
            type="review_completed",
            reference_id=report_id
        )