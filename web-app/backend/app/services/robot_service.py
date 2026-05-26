"""
Thin pass-through over ros_service. We used to persist robot state in a
`robot_status` DB row, but that was redundant — the ROS bridge already owns
the live pose + status, and we have no real battery/hall sensor in Grad I.
Dropping the DB row keeps state in one place and lets us delete the
robot_status table.
"""
from app.services import ros_service


class RobotService:
    @staticmethod
    def get_status() -> dict:
        x, y, _yaw = ros_service.get_pose()
        return {
            "status": ros_service.get_status(),
            "current_x": x,
            "current_y": y,
        }
