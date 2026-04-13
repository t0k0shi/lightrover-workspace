# ライトローバー実機セットアップ チェックリスト

## 1. 準備物

- [ ] Vstone ライトローバー本体
- [ ] Raspberry Pi 4 Model B（4GB RAM）
- [ ] microSD カード（最低 32GB、64GB 以上推奨）
- [ ] USB Type-C 電源アダプタ（5V/3A 以上推奨）または単3ニッケル水素充電池 x4
- [ ] YDLiDAR X2（USB接続）
- [ ] micro HDMI → HDMI アダプタ
- [ ] HDMI モニタ / USB キーボード（初回設定のみ）
- [ ] Wi-Fi ルーター（SSH 接続のため）
- [ ] （オプション）ゲームパッド（DS4 推奨。キーボードでも代替可）

## 2. OS 書き込み

### 2-1. Ubuntu MATE 22.04 イメージの取得

> **なぜ Ubuntu MATE 22.04？**
> ROS 2 Humble は Ubuntu 22.04 LTS を公式サポートしています。
> lightrover_ros2 の humble ブランチもこのバージョン向けです。
>
> **注意**: Vstone 公式 WebDoc の `/setup/softwareSetup/` は
> ROS 1 Melodic + Raspberry Pi OS（Buster）の古い手順です。
> ROS 2 を使う場合はこちらの手順に従ってください。

- [ ] Ubuntu MATE 22.04 の Raspberry Pi 向けイメージをダウンロード
  - 公式: https://ubuntu-mate.org/download/

### 2-2. microSD への書き込み

- [ ] Raspberry Pi Imager をインストール（https://www.raspberrypi.com/software/）
- [ ] Raspberry Pi Imager を起動
- [ ] 「デバイスを選択」→ Raspberry Pi 4 を選択
- [ ] 「OSを選ぶ」→「カスタムイメージを使う」→ ダウンロードした `.img.xz` を選択
- [ ] 「ストレージを選ぶ」→ microSD カードを選択
- [ ] 「次へ」→ 書き込み開始

> **ポイント**: Raspberry Pi Imager には Wi-Fi や SSH を事前設定できるカスタマイズ機能がありますが、
> Ubuntu MATE イメージでは**この機能は使えません**（カスタマイズダイアログが表示されずに書き込みが始まります）。
> 初期設定は次のステップで直接行います。

### 2-3. 初回起動・初期設定

- [ ] microSD を Raspberry Pi に挿入
- [ ] HDMI モニタ（micro HDMI アダプタ経由）とUSB キーボードを接続
- [ ] 電源を接続して起動
- [ ] 初回セットアップウィザードで以下を設定:
  - 言語・キーボードレイアウト
  - ユーザー名・パスワード
  - Wi-Fi（SSID とパスワード）
  - タイムゾーン

### 2-4. SSH 有効化（以降はリモートで作業可能に）

- [ ] ターミナルを開いて SSH を有効化:
  ```bash
  sudo systemctl enable ssh && sudo systemctl start ssh
  ```
- [ ] IP アドレスを確認:
  ```bash
  hostname -I
  ```
- [ ] 手元の PC から SSH 接続を確認:
  ```bash
  ssh <ユーザー名>@<IPアドレス>
  ```

## 3. ROS 2 Humble インストール

> 理由: LTS リリースであり、2027年5月まで公式サポートされます。
> lightrover_ros2 の humble ブランチがこのバージョンに対応しています。

- [ ] ロケールを UTF-8 に設定:
  ```bash
  sudo locale-gen en_US en_US.UTF-8
  sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
  ```
- [ ] ROS 2 apt リポジトリの追加（公式手順に従う）
- [ ] パッケージインストール:
  ```bash
  sudo apt install ros-humble-desktop ros-dev-tools
  ```
- [ ] `.bashrc` に追記:
  ```bash
  echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
  source ~/.bashrc
  ```
- [ ] 動作確認: `ros2 --version` が表示されること

## 4. YDLiDAR X2 ドライバインストール

> 理由: YDLiDAR X2 は 2D LiDAR センサーで、SLAM（slam_toolbox）に使用します。
> ROS2 ドライバが別途必要です。

- [ ] YDLiDAR SDK のクローンとビルド:
  ```bash
  cd ~
  git clone https://github.com/YDLIDAR/YDLidar-SDK.git
  cd YDLidar-SDK && mkdir build && cd build
  cmake .. && make
  sudo make install
  ```
- [ ] ydlidar_ros2_driver のクローン（ros2_ws に配置）:
  ```bash
  cd ~/ros2_ws/src
  git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git
  ```
- [ ] udev ルールの初期化:
  ```bash
  cd ~/ros2_ws/src/ydlidar_ros2_driver/startup
  sudo sh initenv.sh
  ```
- [ ] USB 接続で `/dev/ttyUSB0` が認識されることを確認:
  ```bash
  ls -l /dev/ttyUSB0
  ```

## 5. lightrover_ros2 ビルド

> 理由: 本リポジトリのコアパッケージ群です。公式手順ベースでビルドします。
> 注意: `--parallel-workers 2` は Raspberry Pi のメモリ制約のため。省略するとメモリ不足でビルド失敗の可能性があります。

- [ ] ワークスペースの作成（未作成の場合）: `mkdir -p ~/ros2_ws/src`
- [ ] 本リポジトリを `~/ros2_ws/src/` に配置
- [ ] launch スクリプトに実行権限を付与:
  ```bash
  sudo chmod +x ~/ros2_ws/src/lightrover_ros2/lightrover_ros/lightrover_ros/*.py
  ```
- [ ] ビルド実行:
  ```bash
  cd ~/ros2_ws
  colcon build --symlink-install --cmake-clean-cache --parallel-workers 2
  ```
- [ ] ビルドログにエラーがないことを確認
- [ ] `.bashrc` に追記:
  ```bash
  echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
  source ~/.bashrc
  ```

## 6. デバイス権限の設定

> 理由: ライトローバーの制御基板（VS-WRC201）は I2C 通信、LiDAR は USB シリアルで接続されています。
> デフォルトでは一般ユーザーにアクセス権がありません。

### udev ルールで永続化（推奨）

- [ ] udev ルールファイルを作成:
  ```bash
  sudo tee /etc/udev/rules.d/99-lightrover.rules << 'EOF'
  # I2C (VS-WRC201 制御基板)
  KERNEL=="i2c-*", MODE="0666"
  # USB Serial (YDLiDAR X2)
  KERNEL=="ttyUSB*", MODE="0666"
  EOF
  ```
- [ ] udev ルールを再読込:
  ```bash
  sudo udevadm control --reload-rules && sudo udevadm trigger
  ```

### 手動設定（永続化しない場合、起動のたびに実行）

```bash
sudo chmod 777 /dev/i2c-*
sudo chmod 777 /dev/ttyUSB0
```

## 7. 動作確認（基本 bringup）

> 理由: ビルドが成功しても、実際にモーターやセンサーが応答するかは実機で確認する必要があります。

- [ ] 基本 bringup を実行:
  ```bash
  ros2 launch lightrover_ros nav_base.launch.py
  ```
  > 起動するノード: ydlidar_x2, i2c_controller, odom_manager, pos_controller
- [ ] `ros2 topic list` で以下のトピックが表示されることを確認:
  - `/rover_twist`（速度指令）
  - `/odom`（オドメトリ）
  - `/scan`（LiDAR スキャンデータ）

## 8. YDLiDAR 動作確認

> 理由: SLAM を行う前に、LiDAR 単体でスキャンデータが正しく取得できることを確認します。

- [ ] LiDAR 単体の launch を実行（TF フレーム付き）:
  ```bash
  ros2 launch lightrover_ros ydlidar_x2_launch.py
  ```
- [ ] `ros2 topic echo /scan` でスキャンデータが流れていることを確認
- [ ] rviz2 で `/scan` トピックを表示し、スキャン形状が環境と一致することを確認

## 9. キーボード操作（teleop）

> 理由: SLAM で地図を作成する際、ロボットを手動操作する必要があります。
> キーボード teleop は追加ハードウェア不要で最も手軽な方法です。

- [ ] teleop_twist_keyboard のインストール:
  ```bash
  sudo apt install ros-humble-teleop-twist-keyboard
  ```
- [ ] 追加パッケージのインストール（TF 関連）:
  ```bash
  sudo apt install ros-humble-tf2-tools ros-humble-tf-transformations
  sudo pip install transforms3d
  ```
- [ ] キーボード操作を起動:
  ```bash
  ros2 run teleop_twist_keyboard teleop_twist_keyboard \
    --ros-args --remap cmd_vel:=/rover_twist
  ```
- [ ] 操作方法:
  - `i`: 前進 / `k`: 停止 / `,`: 後退
  - `j`: 左旋回 / `l`: 右旋回
  - `q`/`z`: 最大速度の増減
  - 速度設定の目安: linear=0.1, angular=2.0（ライトローバーは小型のため低速推奨）

## 10. SLAM（地図作成）

> 理由: slam_toolbox を使って環境の2D地図を作成します。自律走行（Nav2）の前提となります。

- [ ] slam_toolbox のインストール:
  ```bash
  sudo apt install ros-humble-slam-toolbox
  ```
- [ ] SLAM を起動:
  ```bash
  ros2 launch lightrover_ros lightrover_slam.launch.py
  ```
- [ ] 別ターミナルでキーボード操作を起動:
  ```bash
  ros2 run teleop_twist_keyboard teleop_twist_keyboard \
    --ros-args --remap cmd_vel:=/rover_twist
  ```
- [ ] ゆっくり走行して地図を作成（急加速・急停止・急旋回は地図が歪む）
- [ ] 地図を保存:
  ```bash
  ros2 run nav2_map_server map_saver_cli \
    -f ~/ros2_ws/src/lightrover_ros2/lightrover_navigation/maps/MAPNAME
  ```

## 11. （オプション）ゲームパッド操作

> ゲームパッド（DS4 等）があれば、より直感的にロボットを操作できます。
> キーボード操作で十分な場合はスキップしてください。

- [ ] 追加パッケージのインストール:
  ```bash
  sudo apt install ros-humble-joy ros-humble-joy-linux
  ```
- [ ] DS4（DualShock 4）を Bluetooth 接続する場合:
  ```bash
  sudo pip install ds4drv
  sudo ds4drv  # その後 PS + SHARE 長押しでペアリング
  ```
- [ ] ゲームパッド操作を起動:
  ```bash
  ros2 launch lightrover_ros pos_joycon.launch.py
  ```
- [ ] 操作方法:
  - 左スティック Y軸: 前後移動（x0.1 m/s）
  - 右スティック X軸: 旋回（x2.0 rad/s）
  - デバイスパスが異なる場合は launch ファイル内の `/dev/input/js0` を変更

## 12. ハマりどころ記録欄

> セットアップ中に発生したエラーと解決方法を記録してください。ブログ記事の素材になります。

| 症状 | 原因 | 解決方法 |
|------|------|---------|
| `/dev/i2c-*` にアクセスできない | 一般ユーザーに権限がない | udev ルール設定（セクション6）または `sudo chmod 777` |
| colcon build でメモリ不足 | 並列ビルドがメモリを消費 | `--parallel-workers 2` を指定 |
| teleop でロボットが動かない | トピック名の不一致 | `--remap cmd_vel:=/rover_twist` を確認 |
| （オプション）ゲームパッドが認識されない | デバイスパスが異なる | `ls /dev/input/js*` で確認し launch ファイルを修正 |
| `sudo apt update` で `NO_PUBKEY F42ED6FBAB17C654` エラー | ROS2 apt リポジトリの GPG 公開鍵が古い | `sudo apt install curl` → `sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg` → `sudo apt update` |
| | | |

## 参考リンク

- [lightrover_ros2 公式リポジトリ](https://github.com/vstoneofficial/lightrover_ros2)
- [ライトローバー WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
- [ROS 2 Humble インストール (Ubuntu)](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)
- [YDLiDAR ROS2 ドライバ](https://github.com/YDLIDAR/ydlidar_ros2_driver)
