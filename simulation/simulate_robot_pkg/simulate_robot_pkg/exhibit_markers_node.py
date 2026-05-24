#!/usr/bin/env python3
"""
exhibit_markers_node.py
Publishes 3 colored exhibit markers on the RViz map.
Runs automatically with the launch file.
"""

import rclpy
from rclpy.node import Node
from visualization_msgs.msg import Marker, MarkerArray
from builtin_interfaces.msg import Duration

# ── 3 exhibit locations (x, y from /clicked_point in RViz) ────
EXHIBITS = [
    {
        "id": 0,
        "name": "Tutankhamun Golden Mask",
        "x": -2.92494535446167,
        "y":  3.9759843349456787,
        "r": 1.0, "g": 0.8, "b": 0.0   # Yellow
    },
    {
        "id": 1,
        "name": "Rosetta Stone",
        "x":  2.0068302154541016,
        "y":  0.941784143447876,
        "r": 1.0, "g": 0.2, "b": 0.2   # Red
    },
    {
        "id": 2,
        "name": "Royal Mummies Chamber",
        "x":  5.001344680786133,
        "y": -2.0101232528686523,
        "r": 0.2, "g": 0.5, "b": 1.0   # Blue
    },
]


class ExhibitMarkersNode(Node):

    def __init__(self):
        super().__init__('exhibit_markers_node')
        self._pub = self.create_publisher(MarkerArray, '/exhibit_markers', 10)
        self.create_timer(1.0, self._publish_markers)
        self.get_logger().info('Exhibit markers node ready.')

    def _publish_markers(self):
        marker_array = MarkerArray()
        for e in EXHIBITS:
            # Sphere
            sphere = Marker()
            sphere.header.frame_id = 'map'
            sphere.header.stamp = self.get_clock().now().to_msg()
            sphere.ns = 'exhibit_spheres'
            sphere.id = e['id']
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = e['x']
            sphere.pose.position.y = e['y']
            sphere.pose.position.z = 0.0
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = 0.3
            sphere.scale.y = 0.3
            sphere.scale.z = 0.3
            sphere.color.r = e['r']
            sphere.color.g = e['g']
            sphere.color.b = e['b']
            sphere.color.a = 1.0
            sphere.lifetime = Duration(sec=2)

            # Text label
            label = Marker()
            label.header.frame_id = 'map'
            label.header.stamp = self.get_clock().now().to_msg()
            label.ns = 'exhibit_labels'
            label.id = e['id']
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose.position.x = e['x']
            label.pose.position.y = e['y']
            label.pose.position.z = 0.5
            label.pose.orientation.w = 1.0
            label.scale.z = 0.25
            label.color.r = 1.0
            label.color.g = 1.0
            label.color.b = 1.0
            label.color.a = 1.0
            label.text = e['name']
            label.lifetime = Duration(sec=2)

            marker_array.markers.append(sphere)
            marker_array.markers.append(label)

        self._pub.publish(marker_array)


def main(args=None):
    rclpy.init(args=args)
    node = ExhibitMarkersNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
