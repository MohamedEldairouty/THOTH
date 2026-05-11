from sqlalchemy.orm import Session

from app.models.robot import NavigationRequest, RobotStatus


class NavigationService:
    @staticmethod
    def start(db: Session, exhibit_id: int) -> NavigationRequest:
        # Mark any in-progress requests as cancelled
        db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).update({"status": "cancelled"})

        nav = NavigationRequest(
            target_exhibit_id=exhibit_id,
            status="in_progress",
            estimated_time=30,  # simulated
        )
        db.add(nav)

        robot = db.query(RobotStatus).first()
        if robot:
            robot.status = "navigating"

        db.commit()
        db.refresh(nav)
        return nav

    @staticmethod
    def stop(db: Session) -> dict:
        db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).update({"status": "cancelled"})

        robot = db.query(RobotStatus).first()
        if robot:
            robot.status = "idle"

        db.commit()
        return {"message": "Navigation stopped"}

    @staticmethod
    def current_status(db: Session) -> NavigationRequest | None:
        return db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).order_by(NavigationRequest.created_at.desc()).first()
