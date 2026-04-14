"""TelemetryBridge: ROS2 /odom, /cmd_vel → InfluxDB Bridge ノード

Lightrover の走行データをリアルタイムで InfluxDB に書き込む。

依存:
    influxdb-client (pip install influxdb-client)
    rclpy, nav_msgs, geometry_msgs (ROS2 Humble 付属)

環境変数:
    ROBOT_ID         ロボット識別子（デフォルト: lightrover_01）
    INFLUXDB_URL     InfluxDB の URL（デフォルト: http://localhost:8086）
    INFLUXDB_TOKEN   認証トークン（必須）
    INFLUXDB_ORG     組織名（デフォルト: lightrover）
    INFLUXDB_BUCKET  バケット名（デフォルト: seminar）
"""

import math
import os

import rclpy
from geometry_msgs.msg import Twist
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import ASYNCHRONOUS
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

# ---------------------------------------------------------------------------
# 純粋関数（ROS2 なしで単体テスト可能）
# ---------------------------------------------------------------------------


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """四元数からヨー角（ラジアン）を求める。

    Args:
        x, y, z, w: 四元数の各成分

    Returns:
        ヨー角 [rad]（-π 〜 π）
    """
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(siny_cosp, cosy_cosp)


def odom_msg_to_point(msg: Odometry, robot_id: str) -> Point:
    """nav_msgs/Odometry メッセージを InfluxDB Point に変換する。

    Measurement: robot_telemetry
    Tags: robot_id
    Fields: pos_x, pos_y, yaw, linear_x, linear_y, angular_z, speed

    Args:
        msg: /odom トピックのメッセージ
        robot_id: ロボット識別子（FR-003）

    Returns:
        InfluxDB Point
    """
    pos = msg.pose.pose.position
    ori = msg.pose.pose.orientation
    vel = msg.twist.twist

    yaw = quaternion_to_yaw(ori.x, ori.y, ori.z, ori.w)
    speed = math.sqrt(vel.linear.x**2 + vel.linear.y**2)

    return (
        Point("robot_telemetry")
        .tag("robot_id", robot_id)
        .field("pos_x", float(pos.x))
        .field("pos_y", float(pos.y))
        .field("yaw", yaw)
        .field("linear_x", float(vel.linear.x))
        .field("linear_y", float(vel.linear.y))
        .field("angular_z", float(vel.angular.z))
        .field("speed", speed)
    )


def cmdvel_msg_to_point(msg: Twist, robot_id: str) -> Point:
    """geometry_msgs/Twist メッセージを InfluxDB Point に変換する。

    Measurement: cmd_vel
    Tags: robot_id
    Fields: linear_x, angular_z

    Args:
        msg: /cmd_vel トピックのメッセージ
        robot_id: ロボット識別子（FR-003）

    Returns:
        InfluxDB Point
    """
    return (
        Point("cmd_vel")
        .tag("robot_id", robot_id)
        .field("linear_x", float(msg.linear.x))
        .field("angular_z", float(msg.angular.z))
    )


# ---------------------------------------------------------------------------
# TelemetryBridge ノード
# ---------------------------------------------------------------------------


class TelemetryBridge(Node):
    """ROS2 /odom, /cmd_vel を InfluxDB に書き込む Bridge ノード。"""

    def __init__(self):
        # Node.__init__ は ROS2 環境でのみノード名を受け取る
        if Node is not object:
            super().__init__("telemetry_bridge")
        else:
            super().__init__()

        # 環境変数から設定を読み込む（FR-003 AC-003-1）
        self._robot_id = os.environ.get("ROBOT_ID", "lightrover_01")
        self._bucket = os.environ.get("INFLUXDB_BUCKET", "seminar")
        self._org = os.environ.get("INFLUXDB_ORG", "lightrover")

        # InfluxDB クライアントを初期化（ASYNCHRONOUS モードで書き込み）
        self._influx_client = InfluxDBClient(
            url=os.environ.get("INFLUXDB_URL", "http://localhost:8086"),
            token=os.environ.get("INFLUXDB_TOKEN", ""),
            org=self._org,
        )
        self._write_api = self._influx_client.write_api(write_options=ASYNCHRONOUS)

        # ROS2 固有の初期化（テスト環境では Node メソッドが存在しないためスキップ）
        try:
            # QoS: BEST_EFFORT（Lightrover /odom パブリッシャーに合わせる）
            qos = QoSProfile(
                depth=10,
                reliability=QoSReliabilityPolicy.BEST_EFFORT,
            )
            self.create_subscription(Odometry, "/odom", self._odom_callback, qos)
            self.create_subscription(Twist, "/cmd_vel", self._cmdvel_callback, 10)
            self.get_logger().info("Subscribed: /odom, /cmd_vel")
        except AttributeError:
            pass

    def _log_error(self, message: str) -> None:
        """ROS2 ロガーが利用可能な場合のみエラーを出力する（テスト環境で安全）。"""
        try:
            self.get_logger().error(message)
        except AttributeError:
            pass

    def _odom_callback(self, msg: Odometry) -> None:
        """/odom コールバック: InfluxDB の robot_telemetry に書き込む。"""
        try:
            point = odom_msg_to_point(msg, self._robot_id)
            self._write_api.write(bucket=self._bucket, org=self._org, record=point)
        except Exception:  # noqa: BLE001
            # InfluxDB 障害でノードがクラッシュしないようにする（AC-002-3）
            self._log_error("Failed to write odom telemetry to InfluxDB")

    def _cmdvel_callback(self, msg: Twist) -> None:
        """/cmd_vel コールバック: InfluxDB の cmd_vel に書き込む。"""
        try:
            point = cmdvel_msg_to_point(msg, self._robot_id)
            self._write_api.write(bucket=self._bucket, org=self._org, record=point)
        except Exception:  # noqa: BLE001
            # InfluxDB 障害でノードがクラッシュしないようにする（AC-002-3）
            self._log_error("Failed to write cmd_vel telemetry to InfluxDB")


# ---------------------------------------------------------------------------
# エントリーポイント
# ---------------------------------------------------------------------------


def main(args=None) -> None:
    """スタンドアロン起動用エントリーポイント。"""
    rclpy.init(args=args)
    node = TelemetryBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
