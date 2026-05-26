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
    from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped  # type: ignore
    from nav2_msgs.action import NavigateToPose  # type: ignore
    from nav2_msgs.srv import ManageLifecycleNodes  # type: ignore
    from lifecycle_msgs.srv import GetState  # type: ignore
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


_initial_pose_pub = None
_amcl_pose_seen = False


def _init_ros() -> None:
    """Spin up an rclpy node in a background thread, then in a separate
    background thread make sure Nav2 lifecycle is active and AMCL has an
    initial pose. Idempotent — calling twice is a no-op."""
    global _ros_node, _ros_executor, _ros_thread, _action_client, _initial_pose_pub
    if not USE_ROS or _ros_node is not None:
        return

    rclpy.init(args=None)
    _ros_node = Node("thoth_web_bridge")

    # ── subscriptions ────────────────────────────────────────────────────
    def on_pose(msg):
        global _amcl_pose_seen
        if not _amcl_pose_seen:
            print("[ros] /amcl_pose received — TF chain is live, ready to navigate.")
        _amcl_pose_seen = True
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        siny = 2.0 * (q.w * q.z + q.x * q.y)
        cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        yaw = math.atan2(siny, cosy)
        with _state.lock:
            _state.x = float(p.x)
            _state.y = float(p.y)
            _state.yaw = yaw

    _ros_node.create_subscription(PoseWithCovarianceStamped, "/amcl_pose", on_pose, 10)

    # ── publishers / clients ─────────────────────────────────────────────
    _action_client = ActionClient(_ros_node, NavigateToPose, "navigate_to_pose")
    _initial_pose_pub = _ros_node.create_publisher(
        PoseWithCovarianceStamped, "/initialpose", 10
    )

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

    # Background worker that brings up Nav2 lifecycle (if not already up) AND
    # — independently — keeps re-publishing /initialpose until AMCL responds.
    # This is the critical fix: previously the initial pose was gated on a
    # successful lifecycle STARTUP, so if Nav2's own bringup had already
    # activated everything, we'd skip the /initialpose publish entirely and
    # AMCL would sit there forever waiting for one.
    threading.Thread(target=_ensure_ready_for_navigation, daemon=True).start()


def init_eager() -> None:
    """Public entry point called from FastAPI startup so the bridge is up
    BEFORE the first user click can reach send_goal."""
    _init_ros()


def _ensure_ready_for_navigation() -> None:
    """Make AMCL produce map→odom, fast.

    Earlier this function called _bring_up_nav2() FIRST and waited for it
    (up to 90s of timeouts if Nav2's lifecycle was already auto-activated by
    the sim team's launch). That blocked /initialpose publishing entirely.

    New strategy: fire the lifecycle STARTUP in a parallel thread (best
    effort, ignored if it fails), and IMMEDIATELY start publishing
    /initialpose every 1s until /amcl_pose comes back. This works whether
    or not lifecycle bringup was needed.
    """
    if not USE_ROS or _ros_node is None:
        return

    # Wait just long enough for AMCL to finish activating + process its
    # first laser scan. Per the sim-team launch logs, that's <3s.
    time.sleep(2.0)

    # Background best-effort lifecycle bringup (no-op if already up).
    def _try_lifecycle():
        try:
            _bring_up_nav2()
        except Exception as e:
            print(f"[ros] lifecycle bringup error (ignored): {e}")
    threading.Thread(target=_try_lifecycle, daemon=True).start()

    # Push /initialpose until AMCL acknowledges. /initialpose is VOLATILE
    # QoS so the first message often gets dropped; we retry until we see
    # /amcl_pose come back, which tells us AMCL has accepted a pose AND
    # produced the map→odom transform.
    for attempt in range(1, 61):  # ~60s total
        if _amcl_pose_seen:
            print(f"[ros] AMCL ready after {attempt} initialpose attempt(s).")
            return
        _publish_initial_pose(0.0, 0.0, 0.0)
        if attempt % 5 == 1:   # log every ~5s to avoid spam
            print(f"[ros]   publishing /initialpose, waiting for /amcl_pose "
                  f"(attempt {attempt}/60)…")
        time.sleep(1.0)

    print("[ros] WARNING: /amcl_pose never arrived after 60s.")
    print("[ros]          Either the robot spawned far from (0,0) — check")
    print("[ros]          `ros2 topic echo /odom --once` and call:")
    print("[ros]          POST /api/robot/lifecycle/initial-pose?x=<X>&y=<Y>")
    print("[ros]          (replace <X>/<Y> with the actual numbers from /odom).")


# ── Nav2 lifecycle bring-up (workaround for the sim team's params) ────────

_LIFECYCLE_MANAGERS = (
    "/lifecycle_manager_localization/manage_nodes",
    "/lifecycle_manager_navigation/manage_nodes",
)


def _bring_up_nav2() -> None:
    """Try a single STARTUP call on each lifecycle manager. Best-effort —
    if Nav2's own launch already activated lifecycle (which the sim team's
    launch does), this will return failure but everything works regardless.

    No retries, short timeouts. We don't want to spend more than ~5s here
    because the parallel initial-pose loop is doing the real work."""
    if not USE_ROS or _ros_node is None:
        return

    for svc_name in _LIFECYCLE_MANAGERS:
        client = _ros_node.create_client(ManageLifecycleNodes, svc_name)
        if not client.wait_for_service(timeout_sec=1.0):
            print(f"[ros] {svc_name}: not available — skipping (sim launch already up?)")
            continue
        req = ManageLifecycleNodes.Request()
        req.command = 0  # STARTUP
        fut = client.call_async(req)
        t0 = time.time()
        while not fut.done() and time.time() - t0 < 2.0:
            time.sleep(0.05)
        if fut.done() and fut.result() and fut.result().success:
            print(f"[ros] {svc_name}: STARTUP OK")
        else:
            print(f"[ros] {svc_name}: STARTUP no-op (lifecycle already active)")


def _publish_initial_pose(x: float, y: float, yaw: float) -> None:
    """Publish to /initialpose so AMCL has a starting estimate.
    Without this AMCL never publishes the map→odom transform."""
    if _initial_pose_pub is None:
        return
    msg = PoseWithCovarianceStamped()
    msg.header.frame_id = "map"
    msg.header.stamp = _ros_node.get_clock().now().to_msg()
    msg.pose.pose.position.x = float(x)
    msg.pose.pose.position.y = float(y)
    # yaw → quaternion
    cz = math.cos(yaw * 0.5)
    sz = math.sin(yaw * 0.5)
    msg.pose.pose.orientation.z = sz
    msg.pose.pose.orientation.w = cz
    # Covariance — small values mean "I'm confident about this estimate"
    cov = [0.0] * 36
    cov[0]  = 0.25   # xx
    cov[7]  = 0.25   # yy
    cov[35] = 0.06853891909122467  # yawyaw
    msg.pose.covariance = cov
    # Publish a few times because /initialpose is volatile
    for _ in range(3):
        _initial_pose_pub.publish(msg)
        time.sleep(0.2)
    print(f"[ros] Published initial pose ({x}, {y}, yaw={yaw}) to /initialpose")


def _send_goal_ros(target_x: float, target_y: float) -> None:
    global _active_goal_handle
    _init_ros()

    print(f"[ros] send_goal({target_x:+.2f}, {target_y:+.2f})  — waiting on action server…")

    # Bring lifecycle up again if needed (idempotent — fast no-op if already active)
    if not _action_client.wait_for_server(timeout_sec=2.0):
        print("[ros]   action server not reachable on first try, triggering Nav2 STARTUP…")
        _bring_up_nav2()
        if not _action_client.wait_for_server(timeout_sec=5.0):
            print("[ros]   STILL not reachable — aborting goal")
            with _state.lock:
                _state.status = "aborted"
            return

    # Critical: bt_navigator rejects goals if there's no map→base_link TF, and
    # AMCL only produces that transform once it has received an initial pose
    # AND processed at least one laser scan. Block here briefly until we see
    # /amcl_pose so the goal won't be rejected for a missing TF.
    if not _amcl_pose_seen:
        print("[ros]   /amcl_pose not seen yet — re-publishing /initialpose and waiting…")
        for _ in range(50):  # up to ~10s
            if _amcl_pose_seen:
                break
            _publish_initial_pose(0.0, 0.0, 0.0)
            time.sleep(0.2)
        if not _amcl_pose_seen:
            print("[ros]   STILL no AMCL pose — TF chain is broken, sending goal will fail")
            with _state.lock:
                _state.status = "aborted"
            return
        print("[ros]   /amcl_pose is live — proceeding with goal.")

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
        try:
            gh = f.result()
        except Exception as e:
            print(f"[ros]   send_goal_async error: {e}")
            with _state.lock:
                _state.status = "aborted"
            return
        _active_goal_handle = gh
        if not gh.accepted:
            print("[ros]   goal REJECTED by bt_navigator (server inactive, or unreachable pose)")
            with _state.lock:
                _state.status = "aborted"
            return
        print(f"[ros]   goal ACCEPTED → robot navigating to ({target_x:+.2f}, {target_y:+.2f})")
        gh.get_result_async().add_done_callback(_on_result)

    fut.add_done_callback(on_response)


def _on_result(rf):
    try:
        result = rf.result()
        code = getattr(result, "status", None)
        print(f"[ros]   goal finished — status code {code}")
    except Exception as e:
        print(f"[ros]   result error: {e}")
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
