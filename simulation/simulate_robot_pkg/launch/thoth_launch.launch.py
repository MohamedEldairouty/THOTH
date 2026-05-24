import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

RVIZ_CONFIG  = '/home/saged/THOTH/simulation.rviz'
PARAMS_FILE  = '/home/saged/THOTH/simulation/simulate_robot_pkg/maps/nav2_params.yaml'


def generate_launch_description():

    map_file   = LaunchConfiguration('map')
    world_file = LaunchConfiguration('world')
    headless   = LaunchConfiguration('headless', default='False')
    rviz_config_file = LaunchConfiguration('rviz_config_file', default=RVIZ_CONFIG)
    params_file      = LaunchConfiguration('params_file',      default=PARAMS_FILE)

    # ── TB3 + Nav2 + RViz ─────────────────────────────────────
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

    # ── Exhibit markers — starts immediately ──────────────────
    exhibit_markers = Node(
        package='simulate_robot_pkg',
        executable='exhibit_markers',
        name='exhibit_markers_node',
        output='screen'
    )

    # ── LLM narration — delayed 5s to let Nav2 start first ────
    llm_narration = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='simulate_robot_pkg',
                executable='llm_narration',
                name='llm_narration_node',
                output='screen',
                emulate_tty=True,
            )
        ]
    )

    return LaunchDescription([
        DeclareLaunchArgument('map',             description='Full path to map.yaml'),
        DeclareLaunchArgument('world',           description='Full path to world file'),
        DeclareLaunchArgument('headless',        default_value='False'),
        DeclareLaunchArgument('rviz_config_file',default_value=RVIZ_CONFIG),
        DeclareLaunchArgument('params_file',     default_value=PARAMS_FILE),

        tb3_launch,
        exhibit_markers,
        llm_narration,
    ])
