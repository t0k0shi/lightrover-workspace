#!/usr/bin/env bash
# setup_vm.sh — NEDOデモ環境 Azure VM 初期セットアップ (v2)
#
# 対象: Ubuntu 24.04 LTS (Noble) + CPU only (Standard_D8s_v3)
# 実行: bash scripts/setup_vm.sh
#
# 設計根拠: docs/specs/nedo-presentation/design.md v2.0.0 §3
# 改訂理由: v1 (Humble + ROSbot XL + GPU) を破棄し、Zenn 4記事ベースの
#          Jazzy + gz sim (Harmonic) + TurtleBot3 + RL 構成に刷新。
#
# セクション:
#   1. 基本パッケージ更新
#   2. ROS2 Jazzy
#   3. ros_gz Harmonic ブリッジ
#   4. TurtleBot3 (Jazzy 公式)
#   5. xrdp + XFCE (software rendering)
#   6. Docker + Docker Compose
#   7. Python venv (~/pyenv_rl_demo)
#   8. lightrover-workspace clone (本リポを clone 済の場合は skip)
#   9. ROS2_Gazebo_RL clone + colcon build

set -euo pipefail

# ── ログ出力 ─────────────────────────────────────────────────────────────────
LOG_FILE="$HOME/setup_vm.log"
exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
log_section() {
  echo
  echo "══════════════════════════════════════════"
  echo "  $*"
  echo "══════════════════════════════════════════"
}

log_section "セットアップ開始 (v2: Ubuntu 24.04 + Jazzy + CPU only)"
log "ログ: $LOG_FILE"
log "ホスト: $(hostname) / OS: $(lsb_release -ds)"

# ── 1. 基本パッケージ更新 ────────────────────────────────────────────────────
log_section "1/9 基本パッケージ更新"
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y \
  curl wget git build-essential software-properties-common \
  apt-transport-https ca-certificates gnupg lsb-release \
  python3-pip python3-venv unzip htop ffmpeg \
  jq vim mesa-utils

# locale 設定（ROS2 が UTF-8 を要求）
sudo apt-get install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# ── 2. ROS2 Jazzy ─────────────────────────────────────────────────────────────
log_section "2/9 ROS2 Jazzy"
if command -v ros2 &>/dev/null && ros2 --version 2>&1 | grep -q jazzy; then
  log "ROS2 Jazzy 既インストール"
else
  log "ROS2 Jazzy をインストール中..."
  # ROS2 GPG キーを追加
  sudo apt-get install -y software-properties-common
  sudo add-apt-repository universe -y

  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list

  sudo apt-get update -y
  sudo apt-get install -y ros-jazzy-desktop
  log "ROS2 Jazzy インストール完了"
fi

# bashrc に source 追加（重複防止）
if ! grep -q "source /opt/ros/jazzy/setup.bash" "$HOME/.bashrc"; then
  echo "source /opt/ros/jazzy/setup.bash" >> "$HOME/.bashrc"
fi

# rosdep 初期化
sudo apt-get install -y python3-rosdep python3-colcon-common-extensions
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  sudo rosdep init || true
fi
rosdep update || true

# ── 3. ros_gz Harmonic ブリッジ ──────────────────────────────────────────────
log_section "3/9 ros_gz (Harmonic + Jazzy bridge)"
sudo apt-get install -y \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-ros-gz-image \
  ros-jazzy-ros-gz-interfaces

log "gz sim version: $(gz sim --version 2>&1 | head -1 || echo 'まだ source されていない可能性')"

# ── 4. TurtleBot3 (Jazzy 公式パッケージ) ─────────────────────────────────────
log_section "4/9 TurtleBot3"
sudo apt-get install -y \
  "ros-jazzy-turtlebot3*" \
  ros-jazzy-teleop-twist-keyboard \
  ros-jazzy-teleop-twist-joy

# モデル指定（Waffle = LiDAR 搭載、デモに適する）
if ! grep -q "TURTLEBOT3_MODEL" "$HOME/.bashrc"; then
  echo "export TURTLEBOT3_MODEL=waffle" >> "$HOME/.bashrc"
fi

# ── 5. xrdp + XFCE (software rendering) ──────────────────────────────────────
log_section "5/9 xrdp + XFCE (software rendering)"
if systemctl is-active --quiet xrdp; then
  log "xrdp 既起動中"
else
  log "XFCE + xrdp をインストール中..."
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    xfce4 xfce4-goodies xorg dbus-x11 x11-xserver-utils
  sudo apt-get install -y xrdp libgl1-mesa-dri
  sudo adduser xrdp ssl-cert || true

  # XFCE をデフォルトセッションに設定
  echo "xfce4-session" | sudo tee /etc/skel/.xsession >/dev/null
  echo "xfce4-session" > "$HOME/.xsession"
  chmod +x "$HOME/.xsession"

  sudo systemctl enable xrdp
  sudo systemctl restart xrdp
  log "xrdp 起動完了 (port 3389)"
fi

# software rendering 強制（GPU なし環境）
if ! grep -q "LIBGL_ALWAYS_SOFTWARE" "$HOME/.bashrc"; then
  cat >> "$HOME/.bashrc" << 'EOF'

# CPU only 環境用: software rendering 強制
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_GL_VERSION_OVERRIDE=3.3
EOF
fi

# ── 6. Docker + Docker Compose ───────────────────────────────────────────────
log_section "6/9 Docker"
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
  log "Docker インストール完了（再ログインで docker グループ反映）"
fi

# ── 7. Python venv (~/pyenv_rl_demo) ─────────────────────────────────────────
log_section "7/9 Python venv (強化学習用)"
if [ ! -d "$HOME/pyenv_rl_demo" ]; then
  python3 -m venv "$HOME/pyenv_rl_demo"
  log "venv 作成: $HOME/pyenv_rl_demo"
fi

# venv 内に SB3 + PyTorch CPU + InfluxDB クライアントをインストール
"$HOME/pyenv_rl_demo/bin/pip" install --upgrade pip
"$HOME/pyenv_rl_demo/bin/pip" install \
  "stable-baselines3[extra]" \
  gymnasium \
  influxdb-client
# PyTorch CPU 版（GPU なしのため CPU index URL を使用）
"$HOME/pyenv_rl_demo/bin/pip" install \
  torch torchvision \
  --index-url https://download.pytorch.org/whl/cpu

# alias 追加
if ! grep -q "alias rl='source ~/pyenv_rl_demo" "$HOME/.bashrc"; then
  echo "alias rl='source ~/pyenv_rl_demo/bin/activate'" >> "$HOME/.bashrc"
fi

# ── 8. lightrover-workspace clone ────────────────────────────────────────────
log_section "8/9 lightrover-workspace"
WS_LR="$HOME/lightrover-workspace"
if [ -d "$WS_LR/.git" ]; then
  log "lightrover-workspace 既 clone 済 ($(cd "$WS_LR" && git rev-parse --short HEAD))"
else
  log "lightrover-workspace を clone 中..."
  git clone https://github.com/t0k0shi/lightrover-workspace.git "$WS_LR"
  log "clone 完了: $(cd "$WS_LR" && git rev-parse --short HEAD)"
fi

# host 側でも influxdb-client を入れておく（Bridge Node 用）
sudo apt-get install -y python3-influxdb-client || \
  pip3 install --user --break-system-packages "influxdb-client>=1.30.0" 2>/dev/null || \
  pip3 install --user "influxdb-client>=1.30.0"

# ── 9. ROS2_Gazebo_RL clone + colcon build ───────────────────────────────────
log_section "9/9 ROS2_Gazebo_RL"
WS_RL="$HOME/ROS2_Gazebo_RL"
if [ -d "$WS_RL/.git" ]; then
  log "ROS2_Gazebo_RL 既 clone 済"
else
  log "ROS2_Gazebo_RL を clone 中..."
  git clone https://github.com/takeofuture/ROS2_Gazebo_RL.git "$WS_RL" || {
    log "WARNING: ROS2_Gazebo_RL の clone に失敗（リポが private/移動の可能性）"
    log "Day 5 に Zenn 記事3 から正しい URL を確認してください"
  }
fi

if [ -d "$WS_RL" ] && [ -f "$WS_RL/requirements.txt" ]; then
  log "ROS2_Gazebo_RL の Python 依存をインストール中..."
  "$HOME/pyenv_rl_demo/bin/pip" install -r "$WS_RL/requirements.txt" 2>&1 | tail -5 || true
fi

if [ -d "$WS_RL" ] && [ -f "$WS_RL/CMakeLists.txt" -o -f "$WS_RL/package.xml" ] || ls "$WS_RL"/src/*/package.xml 2>/dev/null >/dev/null; then
  log "ROS2_Gazebo_RL を colcon build 中..."
  cd "$WS_RL"
  set +u
  source /opt/ros/jazzy/setup.bash
  set -u
  rosdep install --from-paths src --ignore-src -r -y 2>/dev/null || true
  colcon build --symlink-install 2>&1 | tail -20 || log "WARNING: colcon build に失敗"
  if [ -f "$WS_RL/install/setup.bash" ] && ! grep -q "$WS_RL/install/setup.bash" "$HOME/.bashrc"; then
    echo "source $WS_RL/install/setup.bash" >> "$HOME/.bashrc"
  fi
fi

# ── 完了サマリー ──────────────────────────────────────────────────────────────
log_section "セットアップ完了"

cat << EOF

✅ v2 セットアップ完了サマリー
─────────────────────────────────────────
OS              : $(lsb_release -ds)
ROS2            : $(ros2 --version 2>&1 | head -1 || echo "要再ログイン")
gz sim          : $(gz sim --version 2>&1 | head -1 || echo "要再ログイン")
TurtleBot3      : $(dpkg -l 'ros-jazzy-turtlebot3*' 2>/dev/null | grep '^ii' | wc -l) 個のパッケージ
xrdp            : $(systemctl is-active xrdp 2>/dev/null)
Docker          : $(docker --version 2>/dev/null || echo "要再ログイン")
venv (RL)       : $(ls "$HOME/pyenv_rl_demo/bin/python" 2>/dev/null && echo "OK" || echo "未作成")
lightrover-ws   : $([ -d "$WS_LR/.git" ] && echo "OK ($(cd "$WS_LR" && git rev-parse --short HEAD))" || echo "未")
ROS2_Gazebo_RL  : $([ -d "$WS_RL/.git" ] && echo "OK" || echo "Day 5 確認")
─────────────────────────────────────────

確認コマンド:
  source ~/.bashrc
  ros2 --version          # → ros2 jazzy
  gz sim --version        # → Harmonic
  ros2 pkg list | grep turtlebot3 | wc -l  # → 10+
  systemctl is-active xrdp                 # → active
  docker compose version                   # → v2.x (要再ログイン)
  ~/pyenv_rl_demo/bin/python -c "import stable_baselines3; print(stable_baselines3.__version__)"
  curl -s http://localhost:8086/health     # → docker compose up -d 後

次のステップ:
  1. exit でログアウト → 再ログイン（docker グループ反映）
  2. cd ~/lightrover-workspace/telemetry
  3. cp .env.example .env
  4. vi .env  # ROBOT_ID=tb3 を追記、パスワード・トークン設定
  5. docker compose up -d  # InfluxDB + Grafana 起動
  6. xrdp 接続テスト: RDP クライアントから VM:3389 へ

ログ全文: $LOG_FILE
EOF
