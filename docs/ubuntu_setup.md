# THOTH — Ubuntu Setup & Run Guide

End-to-end commands to clone, install, and run the **full integrated stack**
(ROS 2 Nav2 simulation + FastAPI backend + React frontend) on Ubuntu 24.04.

Tested on bare-metal Ubuntu 24.04 with ROS 2 Jazzy.

---

## 0. One-time system install

```bash
sudo apt update && sudo apt install -y software-properties-common curl gnupg
sudo add-apt-repository universe

# ── ROS 2 Jazzy apt repo ──
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
     -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
| sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

sudo apt update

# ── Everything we need ──
sudo apt install -y \
  ros-jazzy-desktop \
  ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-msgs ros-jazzy-turtlebot3-bringup \
  ros-jazzy-rmw-cyclonedds-cpp \
  python3.12 python3.12-venv python3-pip \
  postgresql nodejs npm git

# Use CycloneDDS (default FastDDS has version-mismatch bugs in Jazzy)
echo 'export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp' >> ~/.bashrc
echo 'export TURTLEBOT3_MODEL=waffle'                 >> ~/.bashrc
echo 'source /opt/ros/jazzy/setup.bash'               >> ~/.bashrc
source ~/.bashrc
```

---

## 1. Clone the repo

```bash
cd ~
git clone git@github.com:MohamedEldairouty/THOTH.git
cd THOTH
```

---

## 2. PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER thoth WITH PASSWORD 'thoth_secret';"
sudo -u postgres psql -c "CREATE DATABASE thoth_museum OWNER thoth;"
```

---

## 3. Backend — venv that can see ROS Python bindings

```bash
cd ~/THOTH/web-app/backend

# IMPORTANT: --system-site-packages lets the venv import rclpy from /opt/ros
python3.12 -m venv .venv --system-site-packages
source .venv/bin/activate

pip install -r requirements.txt
# Verify ROS bindings are visible
python -c "import rclpy; print('rclpy OK:', rclpy.__file__)"

# Configure secrets
cp .env.example .env
nano .env   # paste your GEMINI_API_KEY

# DB schema + sync exhibits with simulation positions
alembic upgrade head
python -m app.seed.seed                       # base seed (categories, halls, robot)
python -m app.seed.seed_exhibits              # the 6 final exhibits with full data
python -m app.seed.seed_tours                 # 3 preset tours (Grand / Royal / Artistry)
python -m app.seed.rethemes_map               # re-theme the map.pgm to museum PNG
```

---

## 4. Frontend

```bash
cd ~/THOTH/web-app/frontend
npm install
```

---

## 5. Running the FULL stack

You need **three** terminals — one each for the simulation, the backend,
and the frontend. Run them in this order.

### Terminal 1 — ROS simulation (stock Nav2 + TurtleBot3 + your map)

```bash
source ~/.bashrc

cd ~/THOTH/simulation

ros2 launch nav2_bringup tb3_simulation_launch.py \
  slam:=False \
  map:=$(pwd)/maps/map.yaml \
  world:=$(pwd)/maps/my_custom_world.sdf.xacro \
  headless:=False
```

*Why stock Nav2 and not the simulation team's custom launch?*
Our backend owns all exhibit / tour / LLM logic. We **only** need Nav2's
`/navigate_to_pose` action server and `/amcl_pose` topic from ROS.
The sim team's package has extra nodes (`exhibit_markers_node`,
`llm_narration_node`) that would duplicate or conflict with our work —
running the stock launch ignores them entirely, keeping our system the
single source of truth for exhibits.

Wait until the terminal stops scrolling and you see Gazebo + RViz open.
Then in RViz:

1. Click **`2D Pose Estimate`** → click+drag on the white map where the
   robot is in Gazebo (usually near world origin `0, 0`).
2. Check the terminal stops printing transform errors.
3. Verify Nav2 is fully up:
   ```bash
   # in a 4th terminal, just for the check:
   ros2 action list | grep navigate_to_pose
   # should print:  /navigate_to_pose
   ros2 topic echo /amcl_pose --once --qos-durability transient_local
   # should print pose with x ≈ 0, y ≈ 0
   ```

### Terminal 2 — Backend (FastAPI + ROS bridge)

```bash
# ROS MUST be sourced before activating the venv
source /opt/ros/jazzy/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

cd ~/THOTH/web-app/backend
source .venv/bin/activate

uvicorn app.main:app --reload --port 8001
```

You should see:
```
[ros_service] starting in LIVE (rclpy) mode
[ros] bridge ready — subscribing to /amcl_pose, action: /navigate_to_pose
```
If you instead see `STUB (no ROS)` — your venv can't see `rclpy`.
Re-create it with `--system-site-packages` (step 3 above).

### Terminal 3 — Frontend

```bash
cd ~/THOTH/web-app/frontend
npm run dev -- --host
```

Open `http://localhost:5173` in your browser (or use the LAN IP printed
in the terminal to test on a phone on the same WiFi).

---

## 6. End-to-end test — the "I see the robot moving toward the exhibit" moment

1. Click **Home → Start Tour** (or go directly to `localhost:5173/tour`)
2. Pick **Highlights Tour** (preset)
3. Backend sends Nav2 goal for "Golden Mask of Tutankhamun" at `(-2.92, 3.98)`
4. In Gazebo, the TurtleBot starts driving toward that point
5. In RViz, you see the planned path (green line) + costmap update
6. In the web browser, the **blue robot dot on the map glides toward
   the gold marker** as `/amcl_pose` updates
7. When robot arrives within Nav2's tolerance (~0.25 m), web app status
   flips to `arrived` → "Continue to next exhibit" button appears
8. Click **🎤 Ask THOTH about this exhibit** → existing chat page with
   `?exhibit=<id>` query — Gemini knows which exhibit the visitor is at
9. Click **Continue to next exhibit** → robot drives to Rosetta Stone
10. Repeat → finally **Tour complete** screen

---

## 7. Re-syncing when the simulation team updates the map

When Habiba pushes new `simulation/maps/*` files:

```bash
cd ~/THOTH
git pull

# Refresh the themed museum_map.png
cd web-app/backend
source .venv/bin/activate
python -m app.seed.rethemes_map

# If exhibit positions changed, edit app/seed/sync_with_simulation.py to
# match the new exhibit_markers_node.py coordinates, then:
python -m app.seed.sync_with_simulation

# Restart Terminal 2 (backend) to pick up the new map.yaml
```

---

## 8. Common breakage and quick fixes

| Symptom | Fix |
|---|---|
| `bt_navigator: Action server is inactive` | AMCL didn't get an initial pose — click 2D Pose Estimate in RViz |
| `ros_service` shows STUB mode in backend logs | venv missing rclpy; recreate with `--system-site-packages` |
| Frontend says "Connection error" / port mismatch | Backend not on `8001`. Either start with `--port 8001` or change `vite.config.ts` proxy target |
| Robot drives but blue dot in web doesn't update | Open backend logs — should see no `[ros]` errors. If `subscribe to /amcl_pose` failed, restart Nav2 sim first, then backend |
| symbol lookup error: ...fastcdr... | Make sure `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` is set in **every** terminal (it's in your .bashrc but new terminals must source it) |

---

## 9. Push/pull workflow Windows ↔ Ubuntu

Develop on whichever machine is more comfortable:

- **Windows** — write code, test stub mode, fast iteration on UI
- **Ubuntu** — run real simulation + integration tests

To move work between them:
```bash
# Windows side:
git add -A && git commit -m "WIP" && git push

# Ubuntu side:
git pull
# Restart whatever terminal owns the affected service
```

The backend's `ros_service.py` automatically detects whether ROS is
available — **STUB on Windows**, **LIVE on Ubuntu** — so the same
codebase runs in both places.
