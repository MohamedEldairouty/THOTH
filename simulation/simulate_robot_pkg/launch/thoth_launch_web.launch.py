"""
Web-app friendly launch — same as thoth_launch.launch.py but WITHOUT
the llm_narration node (because the web app's backend owns the LLM and
TTS pipeline; running both would have them both fighting for the mic
and playing audio on top of each other).

Use this when running the web app + ROS together.
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    pkg_share = get_package_share_directory('simulate_robot_pkg')
    nav2_share = get_package_share_directory('nav2_bringup')

    # Defaults resolved from the installed package share dir — no /home/saged paths
    default_params = os.path.join(pkg_share, 'maps', 'nav2_params.yaml')
    default_rviz   = os.path.join(nav2_share, 'rviz', 'nav2_default_view.rviz')

    map_file         = LaunchConfiguration('map')
    world_file       = LaunchConfiguration('world')
    headless         = LaunchConfiguration('headless', default='False')
    rviz_config_file = LaunchConfiguration('rviz_config_file', default=default_rviz)
    params_file      = LaunchConfiguration('params_file',      default=default_params)

    tb3_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('nav2_bringup'),
                'launch',
                'tb3_simulation_launch.py'
            )
        ),
        launch_arguments={
            'slam':             'False',
            'map':              map_file,
            'world':            world_file,
            'headless':         headless,
            'rviz_config_file': rviz_config_file,
            'params_file':      params_file,
        }.items()
    )

    # Visual exhibit markers only (no narration / no Q&A — the web app handles those)
    exhibit_markers = Node(
        package='simulate_robot_pkg',
        executable='exhibit_markers',
        name='exhibit_markers_node',
        output='screen'
    )

    return LaunchDescription([
        DeclareLaunchArgument('map',             description='Full path to map.yaml'),
        DeclareLaunchArgument('world',           description='Full path to world file'),
        DeclareLaunchArgument('headless',        default_value='False'),
        DeclareLaunchArgument('rviz_config_file',default_value=default_rviz),
        DeclareLaunchArgument('params_file',     default_value=default_params),

        tb3_launch,
        exhibit_markers,
    ])
