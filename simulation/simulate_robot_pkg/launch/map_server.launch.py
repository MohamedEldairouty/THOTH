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
    # Required so RViz recognizes the 'map' frame
    static_tf_node = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--yaw', '0', '--pitch', '0', '--roll', '0',
            '--frame-id', 'map',
            '--child-frame-id', 'odom'
        ],
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
        static_tf_node,
        rviz_node,
    ])
