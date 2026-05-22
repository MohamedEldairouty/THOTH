from sqlalchemy.orm import Session

from app.models.robot import RobotStatus
from app.services import ros_service


class RobotService:
    """Reads the robot's live pose from ros_service (stub or real Nav2)
    and keeps the DB row in sync so it survives across restarts."""

    @staticmethod
    def get_status(db: Session) -> RobotStatus:
        robot = db.query(RobotStatus).first()
        if not robot:
            robot = RobotStatus(status="idle", battery=100.0, current_x=3.0, current_y=3.0)
            db.add(robot)
            db.commit()
            db.refresh(robot)

        # Overlay the live pose + status from ros_service
        x, y, _yaw = ros_service.get_pose()
        live_status = ros_service.get_status()
        robot.current_x = x
        robot.current_y = y
        robot.status = live_status
        db.commit()
        db.refresh(robot)
        return robot
