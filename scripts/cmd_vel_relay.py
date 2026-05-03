#!/usr/bin/env python3
"""ROSbot XL シミュレーション用トピックリレー

Humble ros2_controllers の API 変更により、URDF の remapping が機能しないため
このノードでトピック名を橋渡しする。

  /cmd_vel -> /mecanum_drive_controller/reference_unstamped
  /mecanum_drive_controller/odometry -> /odometry/wheels
"""

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node


class RosbotRelay(Node):
    def __init__(self):
        super().__init__("rosbot_relay")
        self.cmd_pub = self.create_publisher(Twist, "/mecanum_drive_controller/reference_unstamped", 10)
        self.cmd_sub = self.create_subscription(Twist, "/cmd_vel", self._cmd_cb, 10)
        self.odom_pub = self.create_publisher(Odometry, "/odometry/wheels", 10)
        self.odom_sub = self.create_subscription(Odometry, "/mecanum_drive_controller/odometry", self._odom_cb, 10)
        self.get_logger().info("relay started: /cmd_vel->reference_unstamped, mecanum/odometry->odometry/wheels")

    def _cmd_cb(self, msg):
        self.cmd_pub.publish(msg)

    def _odom_cb(self, msg):
        self.odom_pub.publish(msg)


def main():
    rclpy.init()
    rclpy.spin(RosbotRelay())


if __name__ == "__main__":
    main()
