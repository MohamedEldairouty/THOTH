# THOTH — Web App

Full-stack touchscreen app for the THOTH museum guide.

🌐 **Live demo:** <https://thoth.thoth-gem.com>

🐧 **Ubuntu launchers:** `tools/ubuntu/`  ·  🪟 **Windows launchers:** `tools/windows/`

---

## 🚀 Ubuntu demo day — the only terminal you run manually

Backend + Cloudflare tunnel are systemd services (see `tools/ubuntu/`),
so the **only** thing left to launch by hand is the sim:

```bash
source /opt/ros/jazzy/setup.bash
source ~/THOTH/simulation/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
ros2 launch simulate_robot_pkg thoth_launch.launch.py
```

Then in RViz: **2D Pose Estimate** → click the robot's spot. Visitors hit
<https://thoth.thoth-gem.com> and start tours.

---

- `backend/` — FastAPI + SQLAlchemy + PostgreSQL, also hosts the ROS bridge (rclpy) when running on Linux.
- `frontend/` — React + Vite + TypeScript + Tailwind. In dev it's served at <http://localhost:5173>; in production it's built into `frontend/dist/` and **served by the backend** on port 8001 so one Cloudflare Tunnel can expose the whole app.

---

## Prereqs

- Python 3.12
- Node 20+
- PostgreSQL 15+ running locally (DB name: `thoth`, see `backend/app/config.py`)
- ffmpeg on `PATH` (Whisper needs it for voice input)
- *(Linux only, optional)* ROS 2 Jazzy sourced — for live Nav2 integration
- *(Linux LIVE only)* the backend venv must be created with
  `python3 -m venv --system-site-packages .venv` so it can see `rclpy`
  from `/opt/ros/jazzy/`. A plain venv silently falls back to STUB mode.
- *(Linux LIVE only)* install Cyclone DDS so the backend matches the sim:
  `sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp`, then
  `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` in **every** terminal
  that talks ROS (sim, backend, `ros2 …` CLI). Mismatched RMW = no
  topics, no actions.

---

## Backend

```bash
cd web-app/backend

# one-time
python -m venv .venv
.venv\Scripts\activate           # Windows (cmd)
# .venv/Scripts/activate         # Windows (PowerShell / Git Bash)
# source .venv/bin/activate      # Linux/Mac
pip install -r requirements.txt

# DB migrations
alembic upgrade head

# seed exhibits + tours
python -m app.seed.seed_exhibits
python -m app.seed.seed_tours

# run
uvicorn app.main:app --reload --port 8001
```

API now at <http://localhost:8001> · Swagger UI at <http://localhost:8001/docs>.

### LIVE vs STUB ROS mode

The backend auto-detects ROS at startup:

- **STUB mode** (Windows or `rclpy` not importable): simulated robot motion. Everything in the web app works end-to-end without a real ROS graph.
- **LIVE mode** (Linux + `rclpy` + Nav2 running): connects to the real `/amcl_pose`, `navigate_to_pose`, and `/initialpose` topics. To force-disable LIVE on Linux, set `ROS_ENABLED=0`.

---

## Frontend

### Dev mode (hot reload, separate port)

```bash
cd web-app/frontend
npm install
npm run dev -- --host          # --host exposes it on the LAN for phones/tablets
```

UI at <http://localhost:5173>. Vite proxies `/api/*` to the backend on `:8001`.

### Production mode (one port, no Vite)

For demos / deployment, build the React bundle and let the backend serve it:

```bash
cd web-app/frontend
npm run build                  # produces frontend/dist/
```

Now the backend (which mounts `dist/` at startup) serves both API **and** UI on port 8001. <http://localhost:8001> shows the full app. One port, one tunnel — that's how the public URL `thoth.thoth-gem.com` works.

---

## Public URL via Cloudflare Tunnel

The demo machine runs `cloudflared` connecting `thoth.thoth-gem.com` → `localhost:8001`

- **Windows** — see `tools/windows/README.md` at the repo root for the
  auto-start `.bat` launchers (uvicorn + cloudflared loops, both wired
  into the Startup folder).
- **Ubuntu** — see `tools/ubuntu/README.md` at the repo root for the
  systemd user service (`thoth-backend.service`) + cloudflared system
  service + the `restart_*.sh` helpers (mirror of the Windows `.bat`s).

---

## Full LIVE stack on Ubuntu

> Shell matters: bash → `setup.bash` (as shown). zsh → swap to `setup.zsh`.
> The `RMW_IMPLEMENTATION` export must come **before** any `ros2` or
> `uvicorn` invocation so child processes inherit it.

Three terminals:

```bash
# T1 — simulation team's launch (Gazebo + Nav2 + map server)
export TURTLEBOT3_MODEL=waffle
ros2 launch simulate_robot_pkg thoth_launch.launch.py

# T2 — backend
cd web-app/backend && source .venv/bin/activate
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
source /opt/ros/jazzy/setup.bash
source ~/THOTH/simulation/install/setup.bash
uvicorn app.main:app --reload --port 8001

# T3 — frontend
cd web-app/frontend && npm run dev -- --host
```

Wait for `[ros] /amcl_pose received — TF chain is live, ready to navigate.` in T2 before clicking Start Tour.

---

## Useful endpoints

| Endpoint | Purpose |
|---|---|
| `GET  /api/robot/diagnostics` | ROS bridge status snapshot (LIVE/STUB, pose, AMCL seen?) |
| `POST /api/robot/lifecycle/startup` | Force Nav2 lifecycle STARTUP |
| `POST /api/robot/lifecycle/initial-pose?x=0&y=0&yaw=0` | Push an initial pose to AMCL |
| `GET  /api/tours/runs/current` | Active tour run + all stops |
| `GET  /api/map` | Map config (resolution, origin) + robot pose |

---

## Common pitfalls

- **`ImportError: edge_tts` in sim logs** — that's the sim team's `llm_narration` node, ignore it. Our backend handles narration via its own `voice_service.py`.
- **`getaddrinfo failed` on `download.pytorch.org`** — flaky DNS. Try `pip install torch` from default PyPI (CPU wheel) or update your DNS to `1.1.1.1`.
- **Goal `REJECTED` on Ubuntu** — AMCL hasn't published `map → odom` yet. Wait for the "TF chain is live" log line. If it never appears, robot is not at (0,0) — push the real pose via `/api/robot/lifecycle/initial-pose`.
- **`AttributeError: module 'coverage.types' has no attribute 'Tracer'`
  on uvicorn startup** — old system `coverage` (e.g. Ubuntu 24.04's
  7.4.4) leaking into the `--system-site-packages` venv is too old for
  the installed `numba`. Fix: `pip install -U coverage` *inside the
  venv* to shadow the system copy.
- **`source: no such file` / `bad substitution` when sourcing ROS** —
  shell vs. setup-file mismatch. Zsh shells (`➜` prompt) need
  `setup.zsh`; bash shells (`$` prompt) need `setup.bash`. Don't mix.