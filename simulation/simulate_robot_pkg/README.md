# Create a workspace

# Unzip into their workspace
cd ~/their_ws/src
unzip simulate_robot_pkg.zip

# Install dependencies
sudo apt install ros-jazzy-nav2-map-server \
                 ros-jazzy-robot-state-publisher \
                 ros-jazzy-joint-state-publisher \
                 ros-jazzy-xacro \
                 ros-jazzy-tf2-ros

# Build
cd ~/their_ws
colcon build --symlink-install
source install/setup.bash

# Launch
ros2 launch simulate_robot_pkg map_server.launch.py
