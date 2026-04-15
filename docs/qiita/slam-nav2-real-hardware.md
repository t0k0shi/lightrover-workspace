# ROS2 ライトローバーで SLAM・Nav2 を実機で動かすまでの道のり

## はじめに

Vstone のライトローバー（Raspberry Pi 4 + YDLiDAR X2）を使って、ROS2 Humble で SLAM による地図作成と Nav2 による自律走行を実機で動かしました。

シミュレーターではなく**実機**でやってみると、ネットで見つからないハマりどころが山盛りでした。この記事はその記録です。

<!-- 画像: ライトローバー実機の外観写真 -->

## 環境

| 項目 | 内容 |
|------|------|
| ロボット | Vstone ライトローバー |
| ボードPC | Raspberry Pi 4 Model B（4GB） |
| OS | Ubuntu MATE 22.04（ヴィストン公式イメージ） |
| ROS | ROS2 Humble |
| LiDAR | YDLiDAR X2（USB接続） |

## 全体の流れ

```
セットアップ → SLAM で地図作成 → 地図を保存 → Nav2 で自律走行
```

## セットアップのポイント

### OS は公式イメージを使う

Ubuntu MATE の汎用イメージではなく、**ヴィストン公式イメージ**（`ubuntu_mate_for_lightrover_20230830.img`）を使います。公式イメージには lightrover 向けの設定が済んでいます。

参考：[公式セットアップ手順](https://vstoneofficial.github.io/lightrover_webdoc/setup/softwareSetupUbuntuRos2_humble/)

### ハマりどころ①：`odom_manager` が起動直後にクラッシュする

`nav_base.launch.py` を起動すると `odom_manager` が即クラッシュしました。

```
[ERROR] [odom_manager_node]: ModuleNotFoundError: No module named 'tf_transformations'
```

**原因：** `tf_transformations` パッケージが不足していた。

**解決：**
```bash
sudo apt install ros-humble-tf-transformations -y
pip install transforms3d
```

### ハマりどころ②：I2C デバイスにアクセスできない

```
[ERROR] Permission denied: '/dev/i2c-1'
```

起動のたびに以下が必要でした：

```bash
sudo chmod 666 /dev/i2c-*
```

永続化したい場合は udev ルールを設定します：

```bash
sudo tee /etc/udev/rules.d/99-lightrover.rules << 'EOF'
KERNEL=="i2c-*", MODE="0666"
KERNEL=="ttyUSB*", MODE="0666"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## SLAM で地図を作る

### 準備：slam_toolbox のインストール

```bash
sudo apt install ros-humble-slam-toolbox -y
```

### 起動手順

**ターミナル1（nav_base）**
```bash
sudo chmod 666 /dev/i2c-*
ros2 launch lightrover_ros nav_base.launch.py
```

**ターミナル2（SLAM）**
```bash
ros2 launch lightrover_ros lightrover_slam.launch.py
```

**ターミナル3（操縦）**
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args --remap cmd_vel:=/rover_twist
```

### LiDAR の CheckSum エラーが大量に出るが動く

```
[error] Check Sum 0x7282 != 0x7A6E
[ERROR] Failed to get scan
```

このエラーが大量に出ても、`/scan` トピックは 11.5Hz で配信されていました。slam_toolbox は欠損スキャンに比較的強いため、地図作成は問題なく動作しました。

```bash
# 動いているか確認
ros2 topic hz /scan
# → average rate: 11.5
```

<!-- 画像: RViz2 で /scan トピックを表示している様子 -->

### 地図が育っているか確認

```bash
ros2 topic hz /map
# → average rate: 1.000
```

1Hz で `/map` が更新されていれば SLAM 動作中です。

<!-- 画像: RViz2 で /map トピックを表示し、地図が育っている様子 -->

### 地図の保存

```bash
ros2 run nav2_map_server map_saver_cli \
  -f ~/ros2_ws/src/lightrover_ros2/lightrover_navigation/maps/my_map
```

`my_map.pgm`（地図画像）と `my_map.yaml`（メタデータ）が生成されます。

<!-- 画像: 保存された my_map.pgm の内容（白黒の2D地図） -->

## Nav2 で自律走行する

### 準備：Nav2 パッケージのインストール

```bash
sudo apt install \
  ros-humble-joint-state-publisher \
  ros-humble-xacro \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup -y
```

### 起動手順

**ターミナル1（nav_base）**
```bash
sudo chmod 666 /dev/i2c-*
ros2 launch lightrover_ros nav_base.launch.py
```

**ターミナル2（Nav2 + RViz2）**
```bash
ros2 launch lightrover_navigation lightrover_navigation.launch.py \
  map:=/home/pi/ros2_ws/src/lightrover_ros2/lightrover_navigation/maps/my_map.yaml
```

### RViz2 で操作する

1. 「**2D Pose Estimate**」でロボットの初期位置を地図上でクリック＆ドラッグ
2. 緑のパーティクル（矢印）が広がればOK
3. 「**2D Nav Goal**」で目的地をクリック＆ドラッグ
4. ロボットが自動で走り始める

<!-- 画像: RViz2 で 2D Nav Goal を設定してロボットが経路計画している様子 -->

<!-- 画像: ロボットが自律走行している様子（動画キャプチャ） -->

### launch ファイルのデフォルト地図名

`lightrover_navigation.launch.py` のデフォルト地図名は `test.yaml` になっています。ファイルを編集せず、起動時に引数で指定する方法が手軽です：

```python
# launch ファイル内のデフォルト値（参考）
map_dir = LaunchConfiguration(
    'map',
    default=os.path.join(..., 'maps', 'test.yaml'))  # ← ここを変える or 引数で上書き
```

```bash
# 引数で指定する方法（ファイル編集不要）
ros2 launch lightrover_navigation lightrover_navigation.launch.py \
  map:=<地図ファイルのフルパス>
```

## まとめ

| やったこと | 結果 |
|-----------|------|
| SLAM で地図作成 | ✅ 動作確認 |
| Nav2 で自律走行 | ✅ 動作確認 |
| udev ルール永続化 | ✅ 設定済み |

LiDAR の CheckSum エラーが出続けても SLAM が動いたのは発見でした。エラーログに惑わされず、実際にトピックが流れているかを `ros2 topic hz` で確認するのが大事です。

## 参考リンク

- [ライトローバー公式 WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
- [ライトローバー公式セットアップ手順](https://vstoneofficial.github.io/lightrover_webdoc/setup/softwareSetupUbuntuRos2_humble/)
- [公式 SLAM 手順](https://vstoneofficial.github.io/lightrover_webdoc/ros2_software_humble/slam/)
- [公式 Nav2 手順](https://vstoneofficial.github.io/lightrover_webdoc/ros2_software_humble/navigation/)
- [lightrover-workspace リポジトリ](https://github.com/t0k0shi/lightrover-workspace)
