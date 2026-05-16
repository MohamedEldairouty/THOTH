# simulate_robot_pkg

A ROS 2 package designed to simulate a 4-wheeled tour guide robot and visualize it alongside a 2D floorplan map inside RViz 2.

---

## Prerequisites

Before using this package, ensure you have the following installed on your system:

- **ROS 2** (Tested on ROS 2 Jazzy / Humble)
- **Nav2 Map Server** (for loading map data)
- **Joint State Publisher** (for managing robot transforms)

You can install the required system dependencies by running:

```bash
sudo apt update
sudo apt install ros-$ROS_DISTRO-nav2-map-server \
                 ros-$ROS_DISTRO-joint-state-publisher \
                 ros-$ROS_DISTRO-robot-state-publisher
```

---

## Installation & Setup

Follow these steps to clone, build, and use this package inside your own ROS 2 workspace.

### 1. Clone the Repository

Navigate to the `src` directory of your ROS 2 workspace and clone this repository from GitHub:

```bash
cd ~/your_workspace/src
git clone https://github.com/YOUR_GITHUB_USERNAME/simulate_robot_pkg.git
```

> Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username or the correct repository URL.

---

### 2. Build the Package

Navigate back to the root of your workspace, build the package, and source the environment variables:

```bash
cd ~/your_workspace
colcon build --packages-select simulate_robot_pkg
source install/setup.bash
```

---

## How to Run

To launch the complete simulation setup — which loads the unified map server, sets up the default static coordinate transforms, initializes the robot states, and opens RViz — run the following command:

```bash
ros2 launch simulate_robot_pkg map_server.launch.py
```

---

## Visualizing the Robot in RViz

Once the launch file triggers RViz, the map will load directly centered over the grid origin `(0,0)`.

To see the robot body model on top of your map canvas, apply these quick settings inside the RViz interface:

1. Locate the **Displays** panel on the left sidebar.
2. Verify that the **Fixed Frame** is set to `map`.
3. Click the **Add** button at the bottom-left corner of the panel.
4. Go to the **By display type** tab, select **RobotModel**, and click **OK**.
5. Click on the newly added **RobotModel** tree node in your sidebar.
6. Look for the **Description Topic** setting and change its value to:

```text
/robot_description
```

Your 4-wheeled tour guide robot will instantly appear sitting right in the center of your map room layout!

---

## Package Directory Structure

```plaintext
simulate_robot_pkg/
├── launch/
│   └── map_server.launch.py   # Unified launch script for maps, transforms, and robot state
├── maps/
│   ├── map.yaml               # Metadata and center-grid alignment configurations
│   └── map.pgm                # 2D Occupancy grid floorplan image
├── urdf/
│   └── robot.urdf             # Physical robot layout profile (links, joints, dimensions)
├── package.xml                # Package dependencies and project metadata
├── setup.py                   # Python installation rules for ROS 2 deployment
└── README.md                  # Setup guide documentation
```
