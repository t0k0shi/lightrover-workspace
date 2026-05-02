#!/usr/bin/env bash
# start_demo.sh — NEDOデモ環境 一括起動スクリプト (v2)
#
# 対象: Ubuntu 24.04 + ROS2 Jazzy + gz sim (Harmonic) + TurtleBot3 + RL
# 使い方:
#   bash scripts/start_demo.sh            # 全プロセス起動 (推論除く)
#   bash scripts/start_demo.sh stop       # 全プロセス停止
#   bash scripts/start_demo.sh inference  # 学習済みモデルで推論起動
#
# 設計根拠: docs/specs/nedo-presentation/design.md v2.0.0 §4
# 起動順序: Docker → gz sim → TB3 spawn → ros_gz_bridge → Bridge Node

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
TELEMETRY_DIR="$WORKSPACE_DIR/telemetry"
BRIDGE_DIR="$TELEMETRY_DIR/bridge"

# v2 固定値
ROBOT_NAME="tb3"
WORLD_NAME="arena"
WORLD_FILE="${WORLD_FILE:-$HOME/rl_demo/worlds/arena.sdf}"
SPAWN_X="${SPAWN_X:--2.5}"
SPAWN_Y="${SPAWN_Y:--2.5}"
SPAWN_Z="${SPAWN_Z:-0.02}"

# RL 推論用
RL_VENV="$HOME/pyenv_rl_demo"
RL_REPO="$HOME/ROS2_Gazebo_RL"
RL_CHECKPOINT="${RL_CHECKPOINT:-$HOME/rl_demo/checkpoints/tb3_ppo_final.zip}"

# ── ログ ────────────────────────────────────────────────────────────────────
log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "[$(date '+%H:%M:%S')] ✅ $*"; }
warn() { echo "[$(date '+%H:%M:%S')] ⚠️  $*"; }
fail() { echo "[$(date '+%H:%M:%S')] ❌ $*"; exit 1; }

# ── 停止処理 ─────────────────────────────────────────────────────────────────
stop_all() {
  log "全プロセスを停止中..."
  pkill -f "tb3_rl"            2>/dev/null || true
  pkill -f "telemetry_bridge.py" 2>/dev/null || true
  pkill -f "ros_gz_bridge"     2>/dev/null || true
  pkill -f "ros_gz_sim"        2>/dev/null || true
  pkill -f "gz sim"            2>/dev/null || true
  pkill -f "ruby.*gz-sim"      2>/dev/null || true
  cd "$TELEMETRY_DIR" && docker compose down 2>/dev/null || true
  ok "停止完了"
  exit 0
}

# ── 推論起動（単独サブコマンド） ──────────────────────────────────────────────
start_inference() {
  log "強化学習 推論モードを起動..."
  [ -d "$RL_VENV" ] || fail "venv が見つかりません: $RL_VENV"
  [ -d "$RL_REPO" ] || fail "ROS2_Gazebo_RL が見つかりません: $RL_REPO"
  [ -f "$RL_CHECKPOINT" ] || warn "チェックポイント未検出: $RL_CHECKPOINT (デフォルトモデルで実行)"

  cd "$RL_REPO"
  set +u
  source /opt/ros/jazzy/setup.bash
  source "$RL_VENV/bin/activate"
  [ -f "$RL_REPO/install/setup.bash" ] && source "$RL_REPO/install/setup.bash"
  set -u

  if [ -f "$RL_CHECKPOINT" ]; then
    python -m tb3_rl.node_bridge --model "$RL_CHECKPOINT"
  else
    python -m tb3_rl.node_bridge
  fi
  exit 0
}

case "${1:-}" in
  stop)      stop_all ;;
  inference) start_inference ;;
esac

# ── ROS2 環境読み込み（Jazzy）— 事前チェックより前に source ─────────────────
set +u
[ -f /opt/ros/jazzy/setup.bash ] && source /opt/ros/jazzy/setup.bash
set -u
export RCUTILS_LOGGING_BUFFERED_STREAM=1
export LIBGL_ALWAYS_SOFTWARE=1   # CPU only 環境

# ── 事前チェック ──────────────────────────────────────────────────────────────
log "事前チェック..."
[ -f "$TELEMETRY_DIR/.env" ] || fail ".env が見つかりません: $TELEMETRY_DIR/.env"
[ -f "$WORLD_FILE" ]         || fail "arena.sdf が見つかりません: $WORLD_FILE"
command -v ros2 &>/dev/null   || fail "ROS2 が見つかりません。/opt/ros/jazzy/setup.bash の source 失敗"
command -v gz   &>/dev/null   || fail "gz sim が見つかりません。apt install ros-jazzy-ros-gz-sim"
command -v docker &>/dev/null || fail "Docker が見つかりません"

# ── Step 1: InfluxDB + Grafana 起動 ──────────────────────────────────────────
log "Step 1/5: InfluxDB + Grafana を起動中..."
cd "$TELEMETRY_DIR"
docker compose up -d
log "  起動待機 30秒..."
sleep 30
if curl -sf http://localhost:8086/health >/dev/null 2>&1; then
  ok "InfluxDB 起動確認"
else
  warn "InfluxDB ヘルスチェック失敗（続行）"
fi
if curl -sf http://localhost:3000/api/health >/dev/null 2>&1; then
  ok "Grafana 起動確認"
else
  warn "Grafana ヘルスチェック失敗（続行）"
fi

# ── ディスプレイ自動検出（GUI モード時のみ）───────────────────────────────────
HEADLESS="${HEADLESS:-0}"
if [ "$HEADLESS" != "1" ]; then
  if [ -z "${DISPLAY:-}" ]; then
    XSOCK=$(ls /tmp/.X11-unix/X* 2>/dev/null | head -1)
    if [ -n "$XSOCK" ]; then
      DISPLAY=":${XSOCK##*X}"
    else
      DISPLAY=:0
    fi
  fi
  export DISPLAY
  log "  使用ディスプレイ: $DISPLAY (GUI モード)"
else
  log "  HEADLESS=1: gz sim を server-only で起動 (GUI 無し)"
fi

# ── Step 2: gz sim 起動（arena ワールド）─────────────────────────────────────
log "Step 2/5: gz sim ($WORLD_NAME world) を起動中..."
GZ_FLAGS="-r"
if [ "$HEADLESS" = "1" ]; then
  GZ_FLAGS="-s -r --headless-rendering"
fi
nohup bash -c "source /opt/ros/jazzy/setup.bash; \
  export DISPLAY=${DISPLAY:-:0}; \
  export LIBGL_ALWAYS_SOFTWARE=1; \
  gz sim $GZ_FLAGS '$WORLD_FILE'" \
  > /tmp/gzsim.log 2>&1 &
GZ_PID=$!
log "  gz sim 起動中 (PID: $GZ_PID)。15秒待機..."
sleep 15
if kill -0 "$GZ_PID" 2>/dev/null; then
  ok "gz sim 起動確認"
else
  fail "gz sim 起動失敗。ログ: tail -f /tmp/gzsim.log"
fi

# ── Step 3: TurtleBot3 Waffle を spawn ───────────────────────────────────────
log "Step 3/5: TurtleBot3 Waffle を spawn 中..."
TB3_MODEL="$(ros2 pkg prefix turtlebot3_gazebo 2>/dev/null)/share/turtlebot3_gazebo/models/turtlebot3_waffle/model.sdf"
if [ ! -f "$TB3_MODEL" ]; then
  TB3_MODEL="/opt/ros/jazzy/share/turtlebot3_gazebo/models/turtlebot3_waffle/model.sdf"
fi
[ -f "$TB3_MODEL" ] || fail "TurtleBot3 model.sdf が見つかりません"

ros2 run ros_gz_sim create \
  -world "$WORLD_NAME" \
  -file "$TB3_MODEL" \
  -name "$ROBOT_NAME" \
  -x "$SPAWN_X" -y "$SPAWN_Y" -z "$SPAWN_Z" \
  > /tmp/tb3_spawn.log 2>&1 &
SPAWN_PID=$!
sleep 5
ok "TB3 spawn コマンド送信 (PID: $SPAWN_PID)"

# ── Step 4: ros_gz_bridge（gz ↔ ROS2 ブリッジ）───────────────────────────────
log "Step 4/5: ros_gz_bridge を起動中..."
nohup bash -c "source /opt/ros/jazzy/setup.bash; \
  ros2 run ros_gz_bridge parameter_bridge \
    /cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist \
    /odom@nav_msgs/msg/Odometry@gz.msgs.Odometry \
    /clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock" \
  > /tmp/rosgzbridge.log 2>&1 &
BRIDGE_PID=$!
log "  ros_gz_bridge 起動中 (PID: $BRIDGE_PID)。5秒待機..."
sleep 5
if kill -0 "$BRIDGE_PID" 2>/dev/null; then
  ok "ros_gz_bridge 起動確認"
else
  warn "ros_gz_bridge が終了。ログ: tail -f /tmp/rosgzbridge.log"
fi

# トピック確認
if ros2 topic list 2>/dev/null | grep -q "/cmd_vel"; then
  ok "/cmd_vel トピック検出"
else
  warn "/cmd_vel トピック未検出（gz sim と bridge の起動完了を待つ）"
fi

# ── Step 5: Bridge Node（ROS2 → InfluxDB）────────────────────────────────────
log "Step 5/5: Bridge Node を起動中..."
set -a
source "$TELEMETRY_DIR/.env"
set +a
export INFLUXDB_URL="${INFLUXDB_URL:-http://localhost:8086}"
export INFLUXDB_BUCKET="${INFLUXDB_BUCKET:-robot_telemetry}"
export INFLUXDB_ORG="${INFLUXDB_ORG:-nedo}"
export INFLUXDB_TOKEN="${INFLUXDB_TOKEN:-please-set-in-env}"
export ROBOT_ID="${ROBOT_ID:-tb3}"
export ODOM_TOPIC="${ODOM_TOPIC:-/odom}"

nohup bash -c "source /opt/ros/jazzy/setup.bash; \
  export INFLUXDB_URL=$INFLUXDB_URL; \
  export INFLUXDB_TOKEN=$INFLUXDB_TOKEN; \
  export INFLUXDB_BUCKET=$INFLUXDB_BUCKET; \
  export INFLUXDB_ORG=$INFLUXDB_ORG; \
  export ROBOT_ID=$ROBOT_ID; \
  export ODOM_TOPIC=$ODOM_TOPIC; \
  cd $BRIDGE_DIR && python3 telemetry_bridge.py" \
  > /tmp/bridge.log 2>&1 &
BNODE_PID=$!
log "  Bridge Node 起動中 (PID: $BNODE_PID)。5秒待機..."
sleep 5
if kill -0 "$BNODE_PID" 2>/dev/null; then
  ok "Bridge Node 起動確認"
else
  warn "Bridge Node が終了。ログ: tail -f /tmp/bridge.log"
fi

# ── 完了メッセージ ────────────────────────────────────────────────────────────
cat << EOF

══════════════════════════════════════════════════════
  ✅ v2 デモ環境 起動完了 (TurtleBot3 + Jazzy + gz sim)
══════════════════════════════════════════════════════

  Grafana       : http://localhost:3000
  InfluxDB UI   : http://localhost:8086
  ロボット      : $ROBOT_NAME (TurtleBot3 Waffle)
  ワールド      : $WORLD_FILE

  手動操縦（RDP ターミナルから）:
    source /opt/ros/jazzy/setup.bash
    ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \\
      "{linear: {x: 0.2}, angular: {z: 0.0}}"

  キーボード操縦:
    ros2 run teleop_twist_keyboard teleop_twist_keyboard

  推論デモ起動（学習完了後）:
    bash scripts/start_demo.sh inference

  ログ確認:
    tail -f /tmp/gzsim.log
    tail -f /tmp/rosgzbridge.log
    tail -f /tmp/bridge.log

  停止:
    bash scripts/start_demo.sh stop

══════════════════════════════════════════════════════
EOF
