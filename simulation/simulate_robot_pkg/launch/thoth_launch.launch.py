import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Resolve everything relative to the installed package share so the launch
    # is portable across machines (no hardcoded /home/<user> paths).
    pkg_share    = get_package_share_directory('simulate_robot_pkg')
    nav2_bringup = get_package_share_directory('nav2_bringup')

    default_map     = os.path.join(pkg_share, 'maps', 'map.yaml')
    default_world   = os.path.join(pkg_share, 'maps', 'my_custom_world.sdf.xacro')
    default_params  = os.path.join(pkg_share, 'maps', 'nav2_params.yaml')
    default_rviz    = os.path.join(nav2_bringup, 'rviz', 'nav2_default_view.rviz')

    map_file         = LaunchConfiguration('map')
    world_file       = LaunchConfiguration('world')
    headless         = LaunchConfiguration('headless')
    rviz_config_file = LaunchConfiguration('rviz_config_file')
    params_file      = LaunchConfiguration('params_file')

    # ── TB3 + Nav2 + RViz (stock nav2_bringup) ────────────────
    tb3_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup, 'launch', 'tb3_simulation_launch.py')
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
        DeclareLaunchArgument('map',              default_value=default_map,
                              description='Full path to map.yaml'),
        DeclareLaunchArgument('world',            default_value=default_world,
                              description='Full path to the Gazebo world file'),
        DeclareLaunchArgument('headless',         default_value='False'),
        DeclareLaunchArgument('rviz_config_file', default_value=default_rviz),
        DeclareLaunchArgument('params_file',      default_value=default_params),

        tb3_launch,
        exhibit_markers,
        llm_narration,
    ])
