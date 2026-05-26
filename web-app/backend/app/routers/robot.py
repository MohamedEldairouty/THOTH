from fastapi import APIRouter

from app.schemas.robot import RobotStatusOut
from app.services.robot_service import RobotService
from app.services import ros_service

router = APIRouter()


@router.get("/status", response_model=RobotStatusOut)
def get_robot_status():
    return RobotService.get_status()


@router.get("/diagnostics")
def get_diagnostics():
    """Backend's view of the ROS bridge. Hit this from the browser to debug
    why a tour might not be moving the simulated robot."""
    x, y, yaw = ros_service.get_pose()
    target_x, target_y = ros_service.get_target()
    return {
        "ros_mode": "LIVE" if ros_service.is_ros_enabled() else "STUB",
        "robot_status": ros_service.get_status(),
        "robot_pose":   {"x": x, "y": y, "yaw": yaw},
        "active_target": {"x": target_x, "y": target_y},
        "amcl_pose_seen": getattr(ros_service, "_amcl_pose_seen", False),
        "tip": (
            "If status stays 'aborted' check backend terminal for [ros] lines. "
            "Open localhost:8001/api/robot/diagnostics in a browser tab while testing."
        ),
    }


@router.post("/lifecycle/startup")
def force_lifecycle_startup():
    """Manually trigger Nav2's lifecycle bring-up. Useful if the backend was
    started before Gazebo/Nav2 finished launching."""
    if not ros_service.is_ros_enabled():
        return {"ok": False, "reason": "Backend is in STUB mode — no ROS available."}
    ros_service._bring_up_nav2()
    return {"ok": True, "msg": "Nav2 lifecycle STARTUP triggered. Check backend terminal."}


@router.post("/lifecycle/initial-pose")
def set_initial_pose(x: float = 0.0, y: float = 0.0, yaw: float = 0.0):
    """Publish an initial pose to /initialpose so AMCL produces the map→odom TF.
    Equivalent to clicking '2D Pose Estimate' in RViz."""
    if not ros_service.is_ros_enabled():
        return {"ok": False, "reason": "STUB mode"}
    ros_service._publish_initial_pose(x, y, yaw)
    return {"ok": True, "msg": f"Initial pose ({x}, {y}, yaw={yaw}) published."}
