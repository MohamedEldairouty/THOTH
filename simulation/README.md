# THOTH Simulation

## Prerequisites

```bash
# Install Python dependencies
pip install edge-tts soundfile sounddevice google-genai python-dotenv openai-whisper

# Install system dependency
sudo apt install libportaudio2 portaudio19-dev
```

## Setup

```bash
# Set Gemini API key
echo 'export GEMINI_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc

# Build the package
cd ~/THOTH/simulation
colcon build --packages-select simulate_robot_pkg
source install/setup.bash
```

## Run

```bash
source /opt/ros/jazzy/setup.bash
export TURTLEBOT3_MODEL=waffle
source ~/THOTH/simulation/install/setup.bash

ros2 launch simulate_robot_pkg thoth_launch.launch.py \
  map:=/home/$USER/THOTH/simulation/maps/map.yaml \
  world:=/home/$USER/THOTH/simulation/maps/my_custom_world.sdf.xacro
```

## Usage

1. Wait for everything to load (~15 seconds)
2. In RViz click **2D Pose Estimate** to set the robot's position on the map
3. Wait for `All exhibits ready!` in the terminal
4. Click **Nav2 Goal** on a colored marker on the map
5. Robot navigates to the exhibit and narrates automatically
6. Ask questions by voice in Arabic or English
