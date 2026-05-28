#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
#  THOTH backend launcher (Ubuntu) — invoked by the systemd user service.
#
#  Unlike the Windows .bat (which loops in shell), Linux uses
#  Restart=always in the .service unit, so this script just execs
#  uvicorn once. systemd respawns it on any exit.
# ────────────────────────────────────────────────────────────────────
set -e

# Source ROS so the backend boots in LIVE mode (rclpy available)
source /opt/ros/jazzy/setup.bash
source "$HOME/THOTH/simulation/install/setup.bash" 2>/dev/null || true
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Force UTF-8 stdio so logs handle Arabic / em-dash / arrows
export PYTHONIOENCODING=utf-8
export PYTHONUTF8=1

cd "$HOME/THOTH/web-app/backend"
# Activate the runtime venv (NOT .venv-train)
# shellcheck disable=SC1091
source .venv/bin/activate

# --host 0.0.0.0 so the LAN (phones on same wifi) can reach it.
# No --reload — this is the demo-day production loop, not dev.
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
