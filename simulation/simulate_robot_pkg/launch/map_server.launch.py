import os
import launch
import launch_ros.actions
import lifecycle_msgs.msg

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler, SetEnvironmentVariable
from launch_ros.actions import LifecycleNode, Node
from launch_ros.events.lifecycle import ChangeState
from launch_ros.event_handlers import OnStateTransition


def generate_launch_description():

    pkg_dir = get_package_share_directory('simulate_robot_pkg')
    map_file = os.path.join(pkg_dir, 'maps', 'map.yaml')

    # --- Path to your URDF file ---
    urdf_file = os.path.join(pkg_dir, 'urdf', 'robot.urdf')
    
    # Read the URDF file content safely
    if os.path.exists(urdf_file):
        with open(urdf_file, 'r') as infp:
            robot_desc = infp.read()
    else:
        robot_desc = ""
        print(f"Warning: URDF file not found at {urdf_file}")

    # --- Fix GLSL rendering issue on some Linux machines ---
    glsl_fix = SetEnvironmentVariable('LIBGL_ALWAYS_SOFTWARE', '1')

    # --- Map Server (lifecycle node) ---
    map_server_node = LifecycleNode(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        namespace='',
        output='screen',
        parameters=[{
            'yaml_filename': map_file,
            'use_sim_time': False
        }]
    )

    # Trigger configure transition on startup
    configure_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=launch.events.matches_action(map_server_node),
            transition_id=lifecycle_msgs.msg.Transition.TRANSITION_CONFIGURE,
        )
    )

    # Trigger activate transition once node reaches inactive state
    activate_event = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=map_server_node,
            goal_state='inactive',
            entities=[
                EmitEvent(event=ChangeState(
                    lifecycle_node_matcher=launch.events.matches_action(map_server_node),
                    transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVATE,
                ))
            ]
        )
    )

    # --- Static TF: map → odom ---
    static_tf_map_to_odom = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_map_to_odom',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--yaw', '0', '--pitch', '0', '--roll', '0',
            '--frame-id', 'map',
            '--child-frame-id', 'odom'
        ],
        output='screen'
    )

    # --- Static TF: odom → base_footprint ---
    # Connects your robot's root frame to your map's coordinate tree
    static_tf_odom_to_footprint = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_odom_to_footprint',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--yaw', '0', '--pitch', '0', '--roll', '0',
            '--frame-id', 'odom',
            '--child-frame-id', 'base_footprint'
        ],
        output='screen'
    )

    # --- Robot State Publisher ---
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_desc}]
    )

    # --- Joint State Publisher ---
    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen'
    )

    # --- RViz ---
    rviz_config = os.path.join(pkg_dir, 'rviz', 'map_view.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config] if os.path.exists(rviz_config) else [],
    )

    return LaunchDescription([
        glsl_fix,
        map_server_node,
        configure_event,
        activate_event,
        static_tf_map_to_odom,
        static_tf_odom_to_footprint,
        robot_state_publisher_node,
        joint_state_publisher_node,
        rviz_node,
    ])
