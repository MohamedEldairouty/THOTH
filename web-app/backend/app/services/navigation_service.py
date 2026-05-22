from sqlalchemy.orm import Session

from app.models.exhibit import Exhibit
from app.models.robot import NavigationRequest, RobotStatus
from app.services import ros_service


class NavigationService:
    @staticmethod
    def start(db: Session, exhibit_id: int) -> NavigationRequest:
        # Cancel any in-progress requests
        db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).update({"status": "cancelled"})

        # Find the target exhibit's world coordinates
        exhibit = db.query(Exhibit).filter(Exhibit.id == exhibit_id).first()
        target_x = float(exhibit.x_position) if exhibit and exhibit.x_position is not None else None
        target_y = float(exhibit.y_position) if exhibit and exhibit.y_position is not None else None

        nav = NavigationRequest(
            target_exhibit_id=exhibit_id,
            status="in_progress",
            estimated_time=30,
        )
        db.add(nav)

        robot = db.query(RobotStatus).first()
        if robot:
            robot.status = "navigating"

        db.commit()
        db.refresh(nav)

        # Dispatch the actual goal — STUB animates, LIVE sends to Nav2
        if target_x is not None and target_y is not None:
            ros_service.send_goal(target_x, target_y)

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

        ros_service.cancel_goal()
        return {"message": "Navigation stopped"}

    @staticmethod
    def current_status(db: Session) -> NavigationRequest | None:
        return db.query(NavigationRequest).filter(
            NavigationRequest.status == "in_progress"
        ).order_by(NavigationRequest.created_at.desc()).first()
