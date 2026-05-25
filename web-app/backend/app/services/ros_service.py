"""
ros_service.py — Bridges the FastAPI backend with the ROS 2 / Nav2 stack.

Two modes auto-selected at startup:

  STUB mode (Windows or rclpy missing):
    Simulates robot motion smoothly toward a goal, pauses at the exhibit,
    then returns to home. Lets the web app demo the navigation story end-to-end
    without a ROS environment.

  LIVE mode (Linux + rclpy + Nav2 stack running):
    Subscribes to /amcl_pose for the live robot position and sends goals to
    the NavigateToPose action server. Same public API.

Public API (mode-agnostic):
    get_pose()      -> (x, y, yaw)
    get_status()    -> "idle" | "navigating" | "completed" | "aborted"
    send_goal(x, y) -> None        (non-blocking)
    cancel_goal()   -> None
    is_ros_enabled() -> bool
"""

import math
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

# ── Try ROS imports; auto-fall back to stub if anything is missing ─────────
_ROS_OK = False
try:
    import rclpy  # type: ignore
    from rclpy.node import Node  # type: ignore
    from rclpy.action import ActionClient  # type: ignore
    from rclpy.executors import SingleThreadedExecutor  # type: ignore
    from geometry_msgs.msg import PoseWithCovarianceStamped  # type: ignore
    from nav2_msgs.action import NavigateToPose  # type: ignore
    _ROS_OK = True
except Exception:
    _ROS_OK = False

USE_ROS = _ROS_OK and os.getenv("ROS_ENABLED", "1") != "0"


# ── Shared robot state ─────────────────────────────────────────────────────

@dataclass
class _RobotState:
    x: float = 3.0
    y: float = 3.0
    yaw: float = 0.0
    status: str = "idle"
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    home_x: float = 3.0
    home_y: float = 3.0
    lock: threading.Lock = field(default_factory=threading.Lock)


_state = _RobotState()


# ── Public API ─────────────────────────────────────────────────────────────

def get_pose() -> tuple[float, float, float]:
    with _state.lock:
        return _state.x, _state.y, _state.yaw


def get_status() -> str:
    with _state.lock:
        return _state.status


def get_target() -> tuple[Optional[float], Optional[float]]:
    with _state.lock:
        return _state.target_x, _state.target_y


def send_goal(target_x: float, target_y: float) -> None:
    if USE_ROS:
        _send_goal_ros(target_x, target_y)
    else:
        _send_goal_stub(target_x, target_y)


def cancel_goal() -> None:
    if USE_ROS:
        _cancel_goal_ros()
    else:
        _cancel_goal_stub()


def is_ros_enabled() -> bool:
    return USE_ROS


# ═══════════════════════════════════════════════════════════════════════════
# STUB MODE — simulated motion (Windows dev, no ROS available)
# ═══════════════════════════════════════════════════════════════════════════

_anim_thread: Optional[threading.Thread] = None
_anim_stop = threading.Event()


def _animate_to(target_x: float, target_y: float) -> None:
    """Smoothly move toward target and STOP there.
    Does not auto-return home — the robot waits at the exhibit until
    the next goal arrives (cancel + new send_goal)."""
    SPEED_MPS = 1.2
    RATE_HZ = 15
    REACH_TOL = 0.10
    dt = 1.0 / RATE_HZ

    with _state.lock:
        _state.status = "navigating"
        _state.target_x = target_x
        _state.target_y = target_y

    while not _anim_stop.is_set():
        with _state.lock:
            dx = target_x - _state.x
            dy = target_y - _state.y
            dist = math.hypot(dx, dy)
            if dist < REACH_TOL:
                _state.x = target_x
                _state.y = target_y
                _state.status = "completed"
                return
            step = min(SPEED_MPS * dt, dist)
            _state.x += dx / dist * step
            _state.y += dy / dist * step
            _state.yaw = math.atan2(dy, dx)
        time.sleep(dt)


def _send_goal_stub(target_x: float, target_y: float) -> None:
    global _anim_thread, _anim_stop
    _cancel_goal_stub()
    _anim_stop = threading.Event()
    _anim_thread = threading.Thread(
        target=_animate_to, args=(target_x, target_y), daemon=True
    )
    _anim_thread.start()


def _cancel_goal_stub() -> None:
    global _anim_thread
    if _anim_thread and _anim_thread.is_alive():
        _anim_stop.set()
        _anim_thread.join(timeout=1.0)
    with _state.lock:
        _state.status = "idle"
        _state.target_x = None
        _state.target_y = None


# ═══════════════════════════════════════════════════════════════════════════
# LIVE MODE — real rclpy bridge (Linux + Nav2 running)
# ═══════════════════════════════════════════════════════════════════════════

_ros_node = None
_ros_executor = None
_ros_thread: Optional[threading.Thread] = None
_action_client = None
_active_goal_handle = None


def _init_ros() -> None:
    """Lazy initializer — spins up an rclpy node in a background thread."""
    global _ros_node, _ros_executor, _ros_thread, _action_client
    if not USE_ROS or _ros_node is not None:
        return

    rclpy.init(args=None)
    _ros_node = Node("thoth_web_bridge")

    def on_pose(msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny, cosy)
        with _state.lock:
            _state.x = float(p.x)
            _state.y = float(p.y)
            _state.yaw = yaw

    _ros_node.create_subscription(
        PoseWithCovarianceStamped, "/amcl_pose", on_pose, 10
    )

    _action_client = ActionClient(_ros_node, NavigateToPose, "navigate_to_pose")

    _ros_executor = SingleThreadedExecutor()
    _ros_executor.add_node(_ros_node)

    def spin():
        try:
            _ros_executor.spin()
        except Exception as e:
            print(f"[ros] spin error: {e}")

    _ros_thread = threading.Thread(target=spin, daemon=True)
    _ros_thread.start()
    print("[ros] bridge ready — subscribing to /amcl_pose, action: /navigate_to_pose")


def _send_goal_ros(target_x: float, target_y: float) -> None:
    global _active_goal_handle
    _init_ros()

    if not _action_client.wait_for_server(timeout_sec=2.0):
        print("[ros] NavigateToPose action server not reachable")
        with _state.lock:
            _state.status = "aborted"
        return

    goal = NavigateToPose.Goal()
    goal.pose.header.frame_id = "map"
    goal.pose.header.stamp = _ros_node.get_clock().now().to_msg()
    goal.pose.pose.position.x = float(target_x)
    goal.pose.pose.position.y = float(target_y)
    goal.pose.pose.orientation.w = 1.0

    with _state.lock:
        _state.status = "navigating"
        _state.target_x = float(target_x)
        _state.target_y = float(target_y)

    fut = _action_client.send_goal_async(goal)

    def on_response(f):
        global _active_goal_handle
        gh = f.result()
        _active_goal_handle = gh
        if not gh.accepted:
            with _state.lock:
                _state.status = "aborted"
            return
        gh.get_result_async().add_done_callback(_on_result)

    fut.add_done_callback(on_response)


def _on_result(rf):
    with _state.lock:
        _state.status = "completed"
        _state.target_x = None
        _state.target_y = None


def _cancel_goal_ros() -> None:
    global _active_goal_handle
    if _active_goal_handle is not None:
        try:
            _active_goal_handle.cancel_goal_async()
        except Exception:
            pass
        _active_goal_handle = None
    with _state.lock:
        _state.status = "idle"
        _state.target_x = None
        _state.target_y = None


# ── Startup banner ─────────────────────────────────────────────────────────
print(f"[ros_service] starting in {'LIVE (rclpy)' if USE_ROS else 'STUB (no ROS)'} mode")
