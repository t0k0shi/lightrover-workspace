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
- [ ] ゲームパッド（DS4 推奨、SLAM 時の手動操作に使用）

## 2. OS 書き込み

### 2-1. ヴィストン公式イメージの取得

> 理由: ヴィストン公式イメージ（`ubuntu_mate_for_lightrover_20230830.img`）は Ubuntu MATE 22.04 ベースで
> lightrover 向けに設定済みです。汎用の Ubuntu MATE イメージではなく公式イメージを使用してください。
> 公式手順: https://vstoneofficial.github.io/lightrover_webdoc/setup/softwareSetupUbuntuRos2_humble/

- [ ] ヴィストン公式イメージ（`ubuntu_mate_for_lightrover_20230830.img`）をダウンロード
  - ダウンロードリンクは公式 WebDoc の手順ページを参照（「Save Link As...」でホームフォルダに保存）
- [ ] balenaEtcher で microSD に書き込み

### 2-2. 初回起動・ネットワーク設定

> 初期ユーザー: `pi` / パスワード: `raspberry`

- [ ] microSD を Raspberry Pi に挿入し、HDMI モニタとキーボードを接続して起動
- [ ] 初回ウィザードでロケール（日本語）、キーボード（日本語 OADG 109A）、Wi-Fi、タイムゾーン（東京）、ユーザーアカウントを設定
- [ ] `hostname -I` で IP アドレスを確認（以降 SSH 接続に使用）
- [ ] SSH を有効化: `sudo systemctl enable ssh && sudo systemctl start ssh`

### 2-3. 自動セットアップスクリプトの実行

> 理由: 公式イメージに付属の `ubuntu22_setup.py` が Raspberry Pi 設定変更と必要ライブラリを一括インストールします。

- [ ] システムアップデートと setuptools のインストール:
  ```bash
  sudo apt update && sudo apt upgrade -y
  sudo apt install python3-setuptools -y
  ```
- [ ] セットアップスクリプトを実行:
  ```bash
  sudo python3 ubuntu22_setup.py
  ```

## 3. ROS 2 Humble インストール

> 理由: LTS リリースであり、2027年5月まで公式サポートされます。
> lightrover_ros2 の humble ブランチがこのバージョンに対応しています。
> 公式手順: https://vstoneofficial.github.io/lightrover_webdoc/setup/softwareSetupUbuntuRos2_humble/

- [ ] ロケールを UTF-8 に設定:
  ```bash
  sudo apt update && sudo apt install locales
  sudo locale-gen en_US en_US.UTF-8
  sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
  export LANG=en_US.UTF-8
  ```
- [ ] ROS 2 apt リポジトリを追加:
  ```bash
  sudo apt install software-properties-common
  sudo add-apt-repository universe
  sudo apt update && sudo apt install curl -y
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
    http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
    | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
  ```
- [ ] パッケージインストール:
  ```bash
  sudo apt update && sudo apt upgrade
  sudo apt install ros-humble-desktop ros-dev-tools
  ```
- [ ] `.bashrc` に追記:
  ```bash
  echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
  source ~/.bashrc
  ```
- [ ] 動作確認: `ros2 --version` が表示されること

## 4. lightrover_ros2 ビルド

> 理由: 本リポジトリのコアパッケージ群です。公式手順ベースでビルドします。
> 注意: `--parallel-workers 2` は Raspberry Pi のメモリ制約のため。省略するとメモリ不足でビルド失敗の可能性があります。

- [ ] ワークスペースを作成:
  ```bash
  mkdir -p ~/ros2_ws/src
  ```
- [ ] lightrover_ros2 をクローン:
  ```bash
  cd ~/ros2_ws/src
  git clone --recursive -b humble https://github.com/vstoneofficial/lightrover_ros2.git
  ```
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

## 5. YDLiDAR X2 ドライバインストール

> 理由: YDLiDAR X2 は 2D LiDAR センサーで、SLAM（slam_toolbox）に使用します。
> ROS2 ドライバが別途必要です。

- [ ] 依存パッケージのインストール:
  ```bash
  sudo apt install cmake pkg-config swig python3-pip -y
  ```
- [ ] YDLiDAR SDK のクローンとビルド:
  ```bash
  cd ~
  git clone https://github.com/YDLIDAR/YDLidar-SDK.git
  cd YDLidar-SDK && mkdir build && cd build
  cmake .. && make
  sudo make install
  ```
- [ ] ydlidar_ros2_driver のクローンとビルド:
  ```bash
  cd ~/ros2_ws/src
  git clone -b humble https://github.com/YDLIDAR/ydlidar_ros2_driver.git
  cd ~/ros2_ws/src/ydlidar_ros2_driver/startup
  sudo chmod 777 ./*
  sudo sh initenv.sh
  cd ~/ros2_ws
  colcon build --symlink-install --cmake-clean-cache --parallel-workers 2
  ```
- [ ] USB 接続で `/dev/ttyUSB0` が認識されることを確認:
  ```bash
  ls -l /dev/ttyUSB0
  ```

## 6. ROS_DOMAIN_ID の設定

> 理由: 同一ネットワーク上の複数機体が混信しないよう、機体ごとに異なる ID を割り当てます。
> DDS によるクロスマシン通信でも、送受信側で ID を揃える必要があります。
> 指定範囲: 0〜65535（同一ネットワーク内で機体ごとに異なる値を使用）

- [ ] `ROS_DOMAIN_ID` を設定（例: 機体1 は `1`、PC は同じ値に揃える）:
  ```bash
  export ROS_DOMAIN_ID=1
  echo "export ROS_DOMAIN_ID=1" >> ~/.bashrc
  source ~/.bashrc
  ```

## 7. デバイス権限の設定

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

## 8. 動作確認（基本 bringup）

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

## 9. YDLiDAR 動作確認

> 理由: SLAM を行う前に、LiDAR 単体でスキャンデータが正しく取得できることを確認します。

- [ ] LiDAR 単体の launch を実行（TF フレーム付き）:
  ```bash
  ros2 launch lightrover_ros ydlidar_x2_launch.py
  ```
- [ ] `ros2 topic echo /scan` でスキャンデータが流れていることを確認
- [ ] rviz2 で `/scan` トピックを表示し、スキャン形状が環境と一致することを確認

## 10. ゲームパッド操作

> 理由: SLAM で地図を作成する際、ゲームパッドでロボットを手動操作する必要があります。

- [ ] 追加パッケージのインストール:
  ```bash
  sudo apt install ros-humble-joy ros-humble-joy-linux \
    ros-humble-tf2-tools ros-humble-tf-transformations
  sudo pip install transforms3d
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

## 11. SLAM（地図作成）

> 理由: slam_toolbox を使って環境の2D地図を作成します。自律走行（Nav2）の前提となります。

- [ ] slam_toolbox のインストール:
  ```bash
  sudo apt install ros-humble-slam-toolbox
  ```
- [ ] SLAM を起動:
  ```bash
  ros2 launch lightrover_ros lightrover_slam.launch.py
  ```
- [ ] 別ターミナルでゲームパッド操作を起動:
  ```bash
  ros2 launch lightrover_ros pos_joycon.launch.py
  ```
- [ ] ゆっくり走行して地図を作成（急加速・急停止・急旋回は地図が歪む）
- [ ] 地図を保存:
  ```bash
  ros2 run nav2_map_server map_saver_cli \
    -f ~/ros2_ws/src/lightrover_ros2/lightrover_navigation/maps/MAPNAME
  ```

## 12. ハマりどころ記録欄

> セットアップ中に発生したエラーと解決方法を記録してください。ブログ記事の素材になります。

| 症状 | 原因 | 解決方法 |
|------|------|---------|
| `/dev/i2c-*` にアクセスできない | 一般ユーザーに権限がない | udev ルール設定（セクション7）または `sudo chmod 777` |
| colcon build でメモリ不足 | 並列ビルドがメモリを消費 | `--parallel-workers 2` を指定 |
| ゲームパッドが認識されない | デバイスパスが異なる | `ls /dev/input/js*` で確認し launch ファイルを修正 |
| | | |

## 参考リンク

- [lightrover_ros2 公式リポジトリ](https://github.com/vstoneofficial/lightrover_ros2)
- [ライトローバー WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
- **[ライトローバー公式セットアップ手順 (Ubuntu + ROS 2 Humble)](https://vstoneofficial.github.io/lightrover_webdoc/setup/softwareSetupUbuntuRos2_humble/)** ← 本チェックリストの参照元
- [ROS 2 Humble インストール (Ubuntu)](https://docs.ros.org/en/humble/Installation/Ubuntu-Install-Debs.html)
- [YDLiDAR ROS2 ドライバ](https://github.com/YDLIDAR/ydlidar_ros2_driver)
