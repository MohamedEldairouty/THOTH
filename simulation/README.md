# THOTH_ws — TurtleBot3 NAV2 Custom Map Simulation

ROS2 Jazzy + Gazebo Harmonic + NAV2 with a custom map.

## Requirements

- Ubuntu 24.04, ROS2 Jazzy, Gazebo Harmonic

```bash
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup \
  ros-jazzy-turtlebot3 ros-jazzy-turtlebot3-msgs \
  ros-jazzy-turtlebot3-bringup ros-jazzy-teleop-twist-keyboard
```

## Run the Simulation

```bash
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=waffle

ros2 launch nav2_bringup tb3_simulation_launch.py \
  slam:=False \
  map:=$(pwd)/maps/map.yaml \
  world:=$(pwd)/maps/my_custom_world.sdf.xacro \
  headless:=False
```

## Navigation

1. In RViz click **2D Pose Estimate** and click where the robot is in Gazebo
2. Click **Nav2 Goal** and click anywhere on the white area of the map
3. The robot will navigate autonomously
