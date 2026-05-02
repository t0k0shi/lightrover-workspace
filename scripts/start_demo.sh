#!/usr/bin/env bash
# start_demo.sh — NEDOデモ環境 一括起動スクリプト
#
# 使い方:
#   bash scripts/start_demo.sh        # 全プロセス起動
#   bash scripts/start_demo.sh stop   # 全プロセス停止
#
# 発表前にこのスクリプトを実行し「起動済み状態」でデモに臨む。
# 起動待ちをデモ中に見せない。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
TELEMETRY_DIR="$WORKSPACE_DIR/telemetry"
BRIDGE_DIR="$TELEMETRY_DIR/bridge"

# ロボットモデルの判定（"ROBOT_TYPE=rosbot_xl" 形式にも対応）
_RAW_TYPE=$(cat "$HOME/.robot_type" 2>/dev/null || echo "rosbot_xl")
ROBOT_TYPE="${_RAW_TYPE#ROBOT_TYPE=}"
ROS2_WS="$HOME/ros2_demo_ws"

# ── ログ ────────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✅ $*"; }
warn() { echo "[$(date '+%H:%M:%S')] ⚠️  $*"; }
fail() { echo "[$(date '+%H:%M:%S')] ❌ $*"; exit 1; }

# ── 停止処理 ─────────────────────────────────────────────────────────────────
stop_all() {
  log "全プロセスを停止中..."
  pkill -f "ros2 launch" 2>/dev/null || true
  pkill -f "telemetry_bridge.py" 2>/dev/null || true
  pkill -f "cmd_vel_relay.py" 2>/dev/null || true
  pkill -f "rviz2" 2>/dev/null || true
  pkill -f "teleop_twist_keyboard" 2>/dev/null || true
  cd "$TELEMETRY_DIR" && docker compose down 2>/dev/null || true
  ok "停止完了"
  exit 0
}

[ "${1:-}" = "stop" ] && stop_all

# ── 事前チェック ──────────────────────────────────────────────────────────────
log "事前チェック..."
[ -f "$TELEMETRY_DIR/.env" ] || fail ".env が見つかりません: $TELEMETRY_DIR/.env"
command -v ros2 &>/dev/null   || fail "ROS2 が見つかりません。source /opt/ros/humble/setup.bash"
command -v docker &>/dev/null || fail "Docker が見つかりません"

# ── ROS2 環境読み込み ─────────────────────────────────────────────────────────
set +u  # ROS2 setup.bash が AMENT_TRACE_SETUP_FILES 未定義変数を使うため
source /opt/ros/humble/setup.bash
[ -f "$ROS2_WS/install/setup.bash" ] && source "$ROS2_WS/install/setup.bash"
set -u
export RCUTILS_LOGGING_BUFFERED_STREAM=1
# gz_ros2_control プラグインパス（controller_manager を Gz Sim で有効化）
export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}
export IGN_GAZEBO_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib:${IGN_GAZEBO_SYSTEM_PLUGIN_PATH:-}

# ── Step 1: InfluxDB + Grafana 起動 ──────────────────────────────────────────
log "Step 1/5: InfluxDB + Grafana を起動中..."
cd "$TELEMETRY_DIR"
docker compose up -d
log "  InfluxDB + Grafana コンテナ起動開始（30秒待機）..."
sleep 30
# ヘルスチェック
if curl -sf http://localhost:8086/health >/dev/null 2>&1; then
  ok "InfluxDB 起動確認"
else
  warn "InfluxDB のヘルスチェック失敗。起動に時間がかかっている可能性あり（続行）"
fi
if curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
  ok "Grafana 起動確認"
else
  warn "Grafana のヘルスチェック失敗（続行）"
fi

# ── Step 2: Gazebo 起動 ───────────────────────────────────────────────────────
log "Step 2/5: Gazebo ($ROBOT_TYPE) を起動中..."
if [ "$ROBOT_TYPE" = "rosbot_xl" ]; then
  GAZEBO_CMD="ros2 launch rosbot_gazebo simulation.launch.py robot_model:=rosbot_xl rviz:=False"
else
  export TURTLEBOT3_MODEL=waffle_pi
  GAZEBO_CMD="ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py"
fi

# ── ディスプレイ自動検出 ──────────────────────────────────────────────────────
# RDP (xrdp) セッションで起動した場合は /tmp/.X11-unix/X* から検出
if [ -z "${DISPLAY:-}" ]; then
  XSOCK=$(ls /tmp/.X11-unix/X* 2>/dev/null | head -1)
  if [ -n "$XSOCK" ]; then
    DISPLAY=":${XSOCK##*X}"
    log "  DISPLAY 自動検出: $DISPLAY"
  else
    DISPLAY=:0
  fi
fi
export DISPLAY
log "  使用ディスプレイ: $DISPLAY"
nohup bash -c "source /opt/ros/humble/setup.bash; \
  [ -f $ROS2_WS/install/setup.bash ] && source $ROS2_WS/install/setup.bash; \
  export LD_LIBRARY_PATH=/opt/ros/humble/lib:\${LD_LIBRARY_PATH:-}; \
  export IGN_GAZEBO_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib:\${IGN_GAZEBO_SYSTEM_PLUGIN_PATH:-}; \
  export GZ_SIM_SYSTEM_PLUGIN_PATH=/opt/ros/humble/lib:\${GZ_SIM_SYSTEM_PLUGIN_PATH:-}; \
  $GAZEBO_CMD" \
  > /tmp/gazebo.log 2>&1 &
GAZEBO_PID=$!
log "  Gazebo 起動中 (PID: $GAZEBO_PID)。20秒待機..."
sleep 20

# トピック確認（mecanum_drive_controller は reference_unstamped を使用）
if ros2 topic list 2>/dev/null | grep -q "mecanum_drive_controller"; then
  ok "Gazebo 起動確認 (mecanum_drive_controller トピック検出)"
elif ros2 topic list 2>/dev/null | grep -q "/cmd_vel"; then
  ok "Gazebo 起動確認 (/cmd_vel トピック検出)"
else
  warn "Gazebo のトピックが未検出。起動に時間がかかっている可能性あり"
  warn "  ログ: tail -f /tmp/gazebo.log"
fi

# ── Step 2.5: Topic Relay Node 起動 ─────────────────────────────────────────
# Humble ros2_controllers API変更のためトピック名をブリッジするリレーノード
# /cmd_vel -> /mecanum_drive_controller/reference_unstamped
# /mecanum_drive_controller/odometry -> /odometry/wheels
log "Step 2.5: Topic Relay Node を起動中..."
nohup bash -c "source /opt/ros/humble/setup.bash; \
  [ -f $ROS2_WS/install/setup.bash ] && source $ROS2_WS/install/setup.bash; \
  python3 $SCRIPT_DIR/cmd_vel_relay.py" \
  > /tmp/relay.log 2>&1 &
RELAY_PID=$!
log "  Relay Node 起動中 (PID: $RELAY_PID)。3秒待機..."
sleep 3
if kill -0 "$RELAY_PID" 2>/dev/null; then
  ok "Topic Relay Node 起動確認"
else
  warn "Relay Node が終了しました"
  warn "  ログ: tail -f /tmp/relay.log"
fi

# ── Step 3: SLAM 起動 ─────────────────────────────────────────────────────────
log "Step 3/5: slam_toolbox を起動中..."
nohup bash -c "source /opt/ros/humble/setup.bash; \
  ros2 launch slam_toolbox online_sync_launch.py use_sim_time:=True" \
  > /tmp/slam.log 2>&1 &
SLAM_PID=$!
log "  slam_toolbox 起動中 (PID: $SLAM_PID)。10秒待機..."
sleep 10
ok "SLAM 起動"

# ── Step 4: Bridge Node 起動 ─────────────────────────────────────────────────
log "Step 4/5: Bridge Node を起動中..."
# .env から環境変数を読み込む（INFLUXDB_TOKEN 等）
set -a; source "$TELEMETRY_DIR/.env"; set +a
export INFLUXDB_URL=http://localhost:8086
export INFLUXDB_BUCKET="${INFLUXDB_BUCKET:-seminar}"
export INFLUXDB_ORG="${INFLUXDB_ORG:-lightrover}"
export INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-lightrover-seminar-token-2026}"
export ROBOT_ID="$ROBOT_TYPE"
# ロボットモデル別の odom トピック
if [ "$ROBOT_TYPE" = "rosbot_xl" ]; then
  export ODOM_TOPIC="/odometry/filtered"  # EKF 出力
else
  export ODOM_TOPIC="/odom"                # TurtleBot3 等は /odom 直接
fi
nohup bash -c "source /opt/ros/humble/setup.bash; \
  [ -f $ROS2_WS/install/setup.bash ] && source $ROS2_WS/install/setup.bash; \
  export INFLUXDB_URL=http://localhost:8086; \
  export INFLUXDB_TOKEN=${INFLUXDB_TOKEN}; \
  export INFLUXDB_BUCKET=${INFLUXDB_BUCKET}; \
  export INFLUXDB_ORG=${INFLUXDB_ORG}; \
  export ROBOT_ID=${ROBOT_ID}; \
  export ODOM_TOPIC=${ODOM_TOPIC}; \
  cd $BRIDGE_DIR && python3 telemetry_bridge.py" \
  > /tmp/bridge.log 2>&1 &
BRIDGE_PID=$!
log "  Bridge Node 起動中 (PID: $BRIDGE_PID)。5秒待機..."
sleep 5
if kill -0 "$BRIDGE_PID" 2>/dev/null; then
  ok "Bridge Node 起動確認"
else
  warn "Bridge Node が終了しました"
  warn "  ログ: tail -f /tmp/bridge.log"
fi

# ── Step 5: RViz2 起動 ───────────────────────────────────────────────────────
log "Step 5/5: RViz2 を起動中..."
RVIZ_CONFIG="$WORKSPACE_DIR/config/demo.rviz"
if [ -f "$RVIZ_CONFIG" ]; then
  nohup bash -c "source /opt/ros/humble/setup.bash; \
    rviz2 -d $RVIZ_CONFIG" \
    > /tmp/rviz2.log 2>&1 &
else
  warn "demo.rviz が見つかりません。デフォルト設定で RViz2 を起動"
  nohup bash -c "source /opt/ros/humble/setup.bash; rviz2" \
    > /tmp/rviz2.log 2>&1 &
fi
ok "RViz2 起動"

# ── 完了メッセージ ────────────────────────────────────────────────────────────
echo
echo "══════════════════════════════════════════════════════"
echo "  ✅ デモ環境 起動完了"
echo "══════════════════════════════════════════════════════"
echo
echo "  Grafana ダッシュボード : http://localhost:3000/d/lightrover-telemetry/robot-telemetry-dashboard"
echo "  InfluxDB UI           : http://localhost:8086"
echo "  ロボットモデル          : $ROBOT_TYPE"
echo
echo "  操縦（RDP ターミナルで）:"
echo "    source /opt/ros/humble/setup.bash"
echo "    source ~/ros2_demo_ws/install/setup.bash"
echo "    ros2 run teleop_twist_keyboard teleop_twist_keyboard"
echo
echo "  ログ確認:"
echo "    tail -f /tmp/gazebo.log"
echo "    tail -f /tmp/relay.log"
echo "    tail -f /tmp/slam.log"
echo "    tail -f /tmp/bridge.log"
echo
echo "  停止:"
echo "    bash scripts/start_demo.sh stop"
echo "══════════════════════════════════════════════════════"
