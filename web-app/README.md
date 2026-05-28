# THOTH — Web App

Full-stack touchscreen app for the THOTH museum guide.

🌐 **Live demo:** <https://thoth.thoth-gem.com>

- `backend/` — FastAPI + SQLAlchemy + PostgreSQL, also hosts the ROS bridge (rclpy) when running on Linux.
- `frontend/` — React + Vite + TypeScript + Tailwind. In dev it's served at <http://localhost:5173>; in production it's built into `frontend/dist/` and **served by the backend** on port 8001 so one Cloudflare Tunnel can expose the whole app.

---

## Prereqs

- Python 3.12
- Node 20+
- PostgreSQL 15+ running locally (DB name: `thoth`, see `backend/app/config.py`)
- ffmpeg on `PATH` (Whisper needs it for voice input)
- *(Linux only, optional)* ROS 2 Jazzy sourced — for live Nav2 integration

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
- **Ubuntu** — see the "Full LIVE stack" section below; both processes
  become systemd services.

---

## Full LIVE stack on Ubuntu

Three terminals:

```bash
# T1 — simulation team's launch (Gazebo + Nav2 + map server)
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
</content>
</invoke>