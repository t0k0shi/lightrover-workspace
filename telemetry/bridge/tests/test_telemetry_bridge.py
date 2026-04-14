"""TelemetryBridge ノードのユニットテスト

TDD: Red → Green → Refactor

テスト方針:
  - 純粋ロジック関数（quaternion_to_yaw, odom_msg_to_point 等）は
    ROS2 なしで直接テストする。
  - TelemetryBridge クラスのコールバックは rclpy.node.Node と
    InfluxDBClient をモックして検証する。
"""

import math
import os
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# rclpy が未インストール環境でもインポートできるようモックを事前注入
# （テスト環境に ROS2 がある場合はそのまま使われる）
if "rclpy" not in sys.modules:
    rclpy_mock = MagicMock()
    rclpy_mock.node.Node = object  # 継承元を object に差し替え
    sys.modules["rclpy"] = rclpy_mock
    sys.modules["rclpy.node"] = rclpy_mock.node
    sys.modules["rclpy.qos"] = MagicMock()
    sys.modules["nav_msgs"] = MagicMock()
    sys.modules["nav_msgs.msg"] = MagicMock()
    sys.modules["geometry_msgs"] = MagicMock()
    sys.modules["geometry_msgs.msg"] = MagicMock()

from telemetry_bridge import cmdvel_msg_to_point, odom_msg_to_point, quaternion_to_yaw

# ---------------------------------------------------------------------------
# quaternion_to_yaw
# ---------------------------------------------------------------------------


class TestQuaternionToYaw(unittest.TestCase):
    """四元数 → ヨー角変換の単体テスト"""

    def test_identity_quaternion_returns_zero(self):
        """単位四元数（回転なし）はヨー角 0.0 rad を返す"""
        yaw = quaternion_to_yaw(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(yaw, 0.0, places=5)

    def test_90_degree_rotation(self):
        """z 軸 90° 回転で π/2 rad を返す"""
        s = math.sqrt(2) / 2
        yaw = quaternion_to_yaw(0.0, 0.0, s, s)
        self.assertAlmostEqual(yaw, math.pi / 2, places=5)

    def test_180_degree_rotation(self):
        """z 軸 180° 回転で π rad（または -π rad）を返す"""
        yaw = quaternion_to_yaw(0.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(abs(yaw), math.pi, places=5)

    def test_negative_rotation(self):
        """z 軸 -90° 回転で -π/2 rad を返す"""
        s = math.sqrt(2) / 2
        yaw = quaternion_to_yaw(0.0, 0.0, -s, s)
        self.assertAlmostEqual(yaw, -math.pi / 2, places=5)


# ---------------------------------------------------------------------------
# odom_msg_to_point
# ---------------------------------------------------------------------------


class TestOdomMsgToPoint(unittest.TestCase):
    """odom_msg_to_point 関数のテスト"""

    def _make_odom_msg(self, x=1.0, y=2.0, qx=0.0, qy=0.0, qz=0.0, qw=1.0, lx=0.3, ly=0.0, az=0.1):
        msg = Mock()
        msg.pose.pose.position.x = x
        msg.pose.pose.position.y = y
        msg.pose.pose.orientation.x = qx
        msg.pose.pose.orientation.y = qy
        msg.pose.pose.orientation.z = qz
        msg.pose.pose.orientation.w = qw
        msg.twist.twist.linear.x = lx
        msg.twist.twist.linear.y = ly
        msg.twist.twist.angular.z = az
        return msg

    def test_measurement_name_is_robot_telemetry(self):
        """measurement 名が 'robot_telemetry' であること（FR-002 AC-002-1）"""
        msg = self._make_odom_msg()
        point = odom_msg_to_point(msg, robot_id="lr_01")
        self.assertEqual(point._name, "robot_telemetry")

    def test_robot_id_tag_is_set(self):
        """robot_id タグが正しく付与されること（FR-003）"""
        msg = self._make_odom_msg()
        point = odom_msg_to_point(msg, robot_id="lightrover_02")
        self.assertEqual(point._tags.get("robot_id"), "lightrover_02")

    def test_pos_x_and_pos_y_fields(self):
        """pos_x, pos_y フィールドが正しく設定されること"""
        msg = self._make_odom_msg(x=1.5, y=2.5)
        point = odom_msg_to_point(msg, robot_id="lr_01")
        fields = point._fields
        self.assertAlmostEqual(fields["pos_x"], 1.5)
        self.assertAlmostEqual(fields["pos_y"], 2.5)

    def test_speed_is_sqrt_of_linear_velocities(self):
        """speed = sqrt(linear_x^2 + linear_y^2) であること（FR-002 AC-002-1）"""
        msg = self._make_odom_msg(lx=0.3, ly=0.4)
        point = odom_msg_to_point(msg, robot_id="lr_01")
        expected_speed = math.sqrt(0.3**2 + 0.4**2)  # 0.5
        self.assertAlmostEqual(point._fields["speed"], expected_speed, places=5)

    def test_speed_is_zero_when_stationary(self):
        """停止中（linear_x=0, linear_y=0）は speed=0 であること"""
        msg = self._make_odom_msg(lx=0.0, ly=0.0)
        point = odom_msg_to_point(msg, robot_id="lr_01")
        self.assertAlmostEqual(point._fields["speed"], 0.0, places=5)

    def test_all_required_fields_exist(self):
        """FR-002 AC-002-1 で定義された全フィールドが存在すること"""
        msg = self._make_odom_msg()
        point = odom_msg_to_point(msg, robot_id="lr_01")
        required = {"pos_x", "pos_y", "yaw", "linear_x", "linear_y", "angular_z", "speed"}
        self.assertEqual(required, set(point._fields.keys()))

    def test_yaw_is_derived_from_quaternion(self):
        """yaw が quaternion から正しく変換されること"""
        # z 軸 90° 回転
        s = math.sqrt(2) / 2
        msg = self._make_odom_msg(qz=s, qw=s)
        point = odom_msg_to_point(msg, robot_id="lr_01")
        self.assertAlmostEqual(point._fields["yaw"], math.pi / 2, places=5)


# ---------------------------------------------------------------------------
# cmdvel_msg_to_point
# ---------------------------------------------------------------------------


class TestCmdvelMsgToPoint(unittest.TestCase):
    """cmdvel_msg_to_point 関数のテスト"""

    def _make_cmdvel_msg(self, lx=0.2, az=0.5):
        msg = Mock()
        msg.linear.x = lx
        msg.angular.z = az
        return msg

    def test_measurement_name_is_cmd_vel(self):
        """measurement 名が 'cmd_vel' であること（FR-002 AC-002-2）"""
        msg = self._make_cmdvel_msg()
        point = cmdvel_msg_to_point(msg, robot_id="lr_01")
        self.assertEqual(point._name, "cmd_vel")

    def test_linear_x_and_angular_z_fields(self):
        """linear_x, angular_z フィールドが正しく設定されること"""
        msg = self._make_cmdvel_msg(lx=0.2, az=-0.5)
        point = cmdvel_msg_to_point(msg, robot_id="lr_01")
        self.assertAlmostEqual(point._fields["linear_x"], 0.2)
        self.assertAlmostEqual(point._fields["angular_z"], -0.5)

    def test_only_two_fields_exist(self):
        """cmd_vel には linear_x と angular_z の 2 フィールドのみ存在すること"""
        msg = self._make_cmdvel_msg()
        point = cmdvel_msg_to_point(msg, robot_id="lr_01")
        self.assertEqual(set(point._fields.keys()), {"linear_x", "angular_z"})

    def test_robot_id_tag_is_set(self):
        """robot_id タグが正しく付与されること（FR-003）"""
        msg = self._make_cmdvel_msg()
        point = cmdvel_msg_to_point(msg, robot_id="lightrover_01")
        self.assertEqual(point._tags.get("robot_id"), "lightrover_01")


# ---------------------------------------------------------------------------
# TelemetryBridge クラス（モック使用）
# ---------------------------------------------------------------------------


class TestTelemetryBridgeCallbacks(unittest.TestCase):
    """TelemetryBridge のコールバック統合テスト"""

    def setUp(self):
        """InfluxDB と rclpy.Node をモックしてインスタンスを生成"""
        with patch.dict(
            os.environ,
            {
                "ROBOT_ID": "test_rover",
                "INFLUXDB_TOKEN": "test-token",
                "INFLUXDB_URL": "http://localhost:8086",
                "INFLUXDB_ORG": "lightrover",
                "INFLUXDB_BUCKET": "seminar",
            },
        ):
            with patch("telemetry_bridge.InfluxDBClient") as mock_client_cls:
                self.mock_write_api = MagicMock()
                mock_client_cls.return_value.write_api.return_value = self.mock_write_api
                from telemetry_bridge import TelemetryBridge

                self.node = TelemetryBridge.__new__(TelemetryBridge)
                TelemetryBridge.__init__(self.node)
                self.TelemetryBridge = TelemetryBridge

    def _make_odom_msg(self):
        msg = Mock()
        msg.pose.pose.position.x = 1.0
        msg.pose.pose.position.y = 2.0
        msg.pose.pose.orientation.x = 0.0
        msg.pose.pose.orientation.y = 0.0
        msg.pose.pose.orientation.z = 0.0
        msg.pose.pose.orientation.w = 1.0
        msg.twist.twist.linear.x = 0.3
        msg.twist.twist.linear.y = 0.0
        msg.twist.twist.angular.z = 0.1
        return msg

    def test_odom_callback_calls_write(self):
        """/odom コールバックが InfluxDB に書き込みを呼ぶこと"""
        msg = self._make_odom_msg()
        self.node._odom_callback(msg)
        self.assertTrue(self.mock_write_api.write.called)

    def test_cmdvel_callback_calls_write(self):
        """/cmd_vel コールバックが InfluxDB に書き込みを呼ぶこと"""
        msg = Mock()
        msg.linear.x = 0.2
        msg.angular.z = 0.0
        self.node._cmdvel_callback(msg)
        self.assertTrue(self.mock_write_api.write.called)

    def test_influxdb_error_does_not_crash(self):
        """InfluxDB への書き込みが失敗してもノードがクラッシュしないこと（AC-002-3）"""
        self.mock_write_api.write.side_effect = Exception("Connection refused")
        msg = self._make_odom_msg()
        # 例外が外に漏れないことを確認
        try:
            self.node._odom_callback(msg)
        except Exception:
            self.fail("_odom_callback raised an exception on InfluxDB error")

    def test_cmdvel_influxdb_error_does_not_crash(self):
        """cmd_vel でも InfluxDB への書き込み失敗でクラッシュしないこと（AC-002-3）"""
        self.mock_write_api.write.side_effect = Exception("Connection refused")
        msg = Mock()
        msg.linear.x = 0.2
        msg.angular.z = 0.0
        try:
            self.node._cmdvel_callback(msg)
        except Exception:
            self.fail("_cmdvel_callback raised an exception on InfluxDB error")

    def test_robot_id_from_env(self):
        """ROBOT_ID 環境変数がタグに反映されること（FR-003 AC-003-1）"""
        self.assertEqual(self.node._robot_id, "test_rover")


if __name__ == "__main__":
    unittest.main()
