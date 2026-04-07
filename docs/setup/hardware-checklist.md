# ライトローバー実機セットアップ チェックリスト

## 1. 準備物

- [ ] Vstone ライトローバー本体
- [ ] YDLiDAR X2（USB接続）
- [ ] microSD カード（32GB以上推奨）
- [ ] HDMI モニタ / キーボード（初回設定のみ）
- [ ] Wi-Fi ルーター（SSH 接続のため）

## 2. OS 書き込み

### 2-1. Ubuntu MATE 22.04 イメージの取得

> 理由: ROS 2 Humble は Ubuntu 22.04 LTS を公式サポートしています。

- [ ] Raspberry Pi 向け Ubuntu MATE 22.04 イメージをダウンロード
- [ ] Raspberry Pi Imager または balenaEtcher で microSD に書き込み

### 2-2. 初回起動・ネットワーク設定

- [ ] microSD を Raspberry Pi に挿入し、HDMI モニタとキーボードを接続して起動
- [ ] 初回起動でユーザー名・パスワードを設定
- [ ] Wi-Fi に接続
- [ ] `hostname -I` で IP アドレスを確認（以降 SSH 接続に使用）

## 3. ROS 2 Humble インストール

> 理由: LTS リリースであり、2027年5月まで公式サポートされます。ライトローバー公式パッケージが Humble 対応です。

- [ ] apt リポジトリの追加（ROS 2 公式手順に従う）
- [ ] `sudo apt install ros-humble-desktop` を実行
- [ ] `.bashrc` に `source /opt/ros/humble/setup.bash` を追記
- [ ] 新しいターミナルで `ros2 --version` が表示されることを確認

## 4. YDLiDAR X2 ドライバインストール

> 理由: YDLiDAR X2 は 2D LiDAR センサーで、SLAM（slam_toolbox）に使用します。ROS2 ドライバが別途必要です。

- [ ] YDLiDAR SDK のクローンとビルド
- [ ] ydlidar_ros2_driver のクローン
- [ ] `colcon build` でドライバをビルド
- [ ] udev ルールの設定（`/dev/ydlidar` の権限付与）
- [ ] USB 接続で `/dev/ttyUSB0` が認識されることを確認

## 5. lightrover_ros2 ビルド

> 理由: 本リポジトリのコアパッケージ群です。公式手順ベースでビルドします。

- [ ] ワークスペースの作成: `mkdir -p ~/ros2_ws/src`
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

## 6. 動作確認

> 理由: ビルドが成功しても、実際にモーターやセンサーが応答するかは実機で確認する必要があります。

- [ ] `.bashrc` に `source ~/ros2_ws/install/setup.bash` を追記
- [ ] bringup launch を実行:
  ```bash
  ros2 launch lightrover_ros lightrover_bringup.launch.py
  ```
- [ ] `ros2 topic list` で `/cmd_vel`, `/odom` 等のトピックが表示されることを確認
- [ ] rqt_robot_steering で手動操作ができることを確認

## 7. YDLiDAR 動作確認

> 理由: SLAM を行う前に、LiDAR 単体でスキャンデータが正しく取得できることを確認します。

- [ ] YDLiDAR launch を実行:
  ```bash
  ros2 launch ydlidar_ros2_driver ydlidar_launch.py
  ```
- [ ] `ros2 topic echo /scan` でスキャンデータが流れていることを確認
- [ ] rviz2 で `/scan` トピックを表示し、スキャン形状が環境と一致することを確認

## 8. ハマりどころ記録欄

> セットアップ中に発生したエラーと解決方法を記録してください。ブログ記事の素材になります。

| 症状 | 原因 | 解決方法 |
|------|------|---------|
| | | |
