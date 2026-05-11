from sqlalchemy.orm import Session

from app.models.robot import RobotStatus


class RobotService:
    @staticmethod
    def get_status(db: Session) -> RobotStatus:
        robot = db.query(RobotStatus).first()
        if not robot:
            robot = RobotStatus(status="idle", battery=100.0, current_x=0.0, current_y=0.0)
            db.add(robot)
            db.commit()
            db.refresh(robot)
        return robot
