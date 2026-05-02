#!/usr/bin/env bash
# setup_vm.sh — NEDOデモ環境 Azure VM 初期セットアップ
#
# 対象: Ubuntu 22.04 LTS + NVIDIA Tesla T4 (NC4as_T4_v3)
# 実行: bash scripts/setup_vm.sh
#
# セクション:
#   1. NVIDIA ドライバ + CUDA
#   2. Docker + Docker Compose
#   3. xrdp + XFCE デスクトップ
#   4. ROS2 Humble
#   5. ROSbot XL シミュレーション (フォールバック: TurtleBot3)
#   6. Python 依存 (influxdb-client)
#   7. lightrover-workspace セットアップ

set -euo pipefail

# ── ログ出力 ─────────────────────────────────────────────────────────────────
LOG_FILE="$HOME/setup_vm.log"
exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
log_section() { echo; echo "══════════════════════════════════════════"; echo "  $*"; echo "══════════════════════════════════════════"; }

log_section "セットアップ開始"
log "ログ: $LOG_FILE"

# ── 1. システム更新 ──────────────────────────────────────────────────────────
log_section "1/7 システム更新"
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y \
  curl wget git build-essential software-properties-common \
  apt-transport-https ca-certificates gnupg lsb-release \
  python3-pip python3-venv unzip htop

# ── 2. NVIDIA ドライバ + CUDA ─────────────────────────────────────────────────
log_section "2/7 NVIDIA ドライバ"
if nvidia-smi &>/dev/null; then
  log "GPU 認識済み、ドライバインストールをスキップ"
else
  log "NVIDIA ドライバをインストール中..."
  sudo apt-get install -y ubuntu-drivers-common
  sudo ubuntu-drivers autoinstall
  log "ドライバインストール完了。GPU確認は再起動後に実施"
fi

# ── 3. Docker + Docker Compose ───────────────────────────────────────────────
log_section "3/7 Docker"
if command -v docker &>/dev/null; then
  log "Docker 既インストール: $(docker --version)"
else
  log "Docker をインストール中..."
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker "$USER"
  log "Docker インストール完了"
fi

# ── 4. xrdp + XFCE デスクトップ ─────────────────────────────────────────────
log_section "4/7 xrdp + XFCE"
if systemctl is-active --quiet xrdp; then
  log "xrdp 既起動中"
else
  log "XFCE + xrdp をインストール中..."
  sudo apt-get install -y xfce4 xfce4-goodies xorg dbus-x11 x11-xserver-utils
  sudo apt-get install -y xrdp
  sudo adduser xrdp ssl-cert

  # XFCE をデフォルトセッションに設定
  echo "xfce4-session" | sudo tee /etc/skel/.xsession
  echo "xfce4-session" > "$HOME/.xsession"
  chmod +x "$HOME/.xsession"

  # xrdp のポート確認・起動
  sudo systemctl enable xrdp
  sudo systemctl restart xrdp
  log "xrdp 起動完了 (port 3389)"
fi

# NVIDIA OpenGL 設定（Gazebo 描画用）
if nvidia-smi &>/dev/null; then
  log "NVIDIA OpenGL 環境変数を設定"
  cat >> "$HOME/.bashrc" << 'EOF'

# NVIDIA OpenGL for xrdp (Gazebo 描画)
export LIBGL_ALWAYS_INDIRECT=0
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
EOF
fi

# ── 5. ROS2 Humble ───────────────────────────────────────────────────────────
log_section "5/7 ROS2 Humble"
if command -v ros2 &>/dev/null; then
  log "ROS2 既インストール: $(ros2 --version 2>&1 | head -1)"
else
  log "ROS2 Humble をインストール中..."
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list
  sudo apt-get update -y
  sudo apt-get install -y ros-humble-desktop
  log "ROS2 Humble インストール完了"
fi

# ROS2 追加パッケージ
log "ROS2 追加パッケージをインストール中..."
sudo apt-get install -y \
  ros-humble-slam-toolbox \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-teleop-twist-keyboard \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-gazebo-ros2-control \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-humble-tf-transformations

# ROS2 環境変数を bashrc に追加
if ! grep -q "source /opt/ros/humble/setup.bash" "$HOME/.bashrc"; then
  echo "source /opt/ros/humble/setup.bash" >> "$HOME/.bashrc"
fi

# rosdep 初期化
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init
fi
rosdep update

# ── 6. ROSbot XL シミュレーション ────────────────────────────────────────────
log_section "6/7 ROSbot XL Gazebo シミュレーション"

WS="$HOME/ros2_demo_ws"
ROSBOT_OK=false

# ROSbot XL ビルドを試みる
if [ ! -d "$WS/src/rosbot_ros" ]; then
  log "husarion/rosbot_ros をクローン中..."
  mkdir -p "$WS/src"
  cd "$WS/src"
  git clone --depth 1 https://github.com/husarion/rosbot_ros.git || {
    log "WARNING: rosbot_ros クローン失敗。TurtleBot3 フォールバックを使用"
  }
fi

if [ -d "$WS/src/rosbot_ros" ]; then
  log "ROSbot XL ビルド中 (colcon)..."
  cd "$WS"
  set +u  # ROS2 setup.bash が AMENT_TRACE_SETUP_FILES 未定義変数を使うため一時的に -u を無効化
  source /opt/ros/humble/setup.bash
  set -u
  # 依存解決
  rosdep install --from-paths src --ignore-src -r -y 2>/dev/null || true
  # ビルド (--continue-on-error で部分失敗を許容)
  if colcon build --symlink-install --packages-select rosbot_description rosbot_gazebo 2>/dev/null; then
    ROSBOT_OK=true
    log "ROSbot XL ビルド成功"
    echo "source $WS/install/setup.bash" >> "$HOME/.bashrc"
  else
    log "WARNING: ROSbot XL ビルド失敗 → TurtleBot3 フォールバック"
  fi
fi

# TurtleBot3 フォールバック
if [ "$ROSBOT_OK" = false ]; then
  log "TurtleBot3 Waffle Pi をインストール中..."
  sudo apt-get install -y \
    ros-humble-turtlebot3-gazebo \
    ros-humble-turtlebot3-cartographer \
    ros-humble-turtlebot3-navigation2
  if ! grep -q "TURTLEBOT3_MODEL" "$HOME/.bashrc"; then
    echo "export TURTLEBOT3_MODEL=waffle_pi" >> "$HOME/.bashrc"
  fi
  log "TurtleBot3 フォールバック完了"
  echo "ROBOT_TYPE=turtlebot3" > "$HOME/.robot_type"
else
  echo "ROBOT_TYPE=rosbot_xl" > "$HOME/.robot_type"
fi

# ── 7. Python 依存 ────────────────────────────────────────────────────────────
log_section "7/7 Python 依存 (influxdb-client)"
pip3 install --user "influxdb-client>=1.30.0"

# ── 完了サマリー ──────────────────────────────────────────────────────────────
log_section "セットアップ完了"

ROBOT_TYPE=$(cat "$HOME/.robot_type" 2>/dev/null || echo "unknown")

cat << EOF

✅ セットアップ完了サマリー
─────────────────────────────────────────
NVIDIA ドライバ : $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo "未確認（再起動後に確認）")
Docker          : $(docker --version 2>/dev/null || echo "要再ログイン")
xrdp            : $(systemctl is-active xrdp 2>/dev/null)
ROS2            : $(ros2 --version 2>/dev/null | head -1 || echo "要ターミナル再起動")
ロボットモデル    : $ROBOT_TYPE
influxdb-client : $(pip3 show influxdb-client 2>/dev/null | grep Version || echo "インストール済")
─────────────────────────────────────────

次のステップ:
  1. sudo reboot  ← NVIDIA ドライバを有効化
  2. 再起動後: nvidia-smi で GPU 確認
  3. cd ~/my-issue-oss/lightrover-workspace/telemetry
     cp .env.example .env
     vi .env  # パスワード・トークンを設定
     docker compose up -d

ログ全文: $LOG_FILE
EOF
