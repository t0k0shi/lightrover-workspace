# ライトローバー ROS2 セットアップメモ（ハマりどころ集）

この記事は「[Raspberry Pi のロボットで地図を作って自動走行させた！（SLAM / Nav2）](./slam-nav2-real-hardware.md)」のセットアップ詳細版だ。

## 環境

| 項目 | 内容 |
|------|------|
| ロボット | Vstone ライトローバー |
| ボードPC | Raspberry Pi 4 Model B（4GB） |
| OS | Ubuntu MATE 22.04（ヴィストン公式イメージ） |
| ROS | ROS2 Humble |
| LiDAR | YDLiDAR X2（USB接続） |

## OS は公式イメージを使う

Ubuntu MATE の汎用イメージではなく、ヴィストン公式イメージ（`ubuntu_mate_for_lightrover_20230830.img`）を使う。公式イメージには lightrover 向けの設定が済んでいる。

参考：[公式セットアップ手順](https://vstoneofficial.github.io/lightrover_webdoc/setup/softwareSetupUbuntuRos2_humble/)

## 必要パッケージのインストール

### SLAM 用

```bash
sudo apt install ros-humble-slam-toolbox -y
```

### Nav2 用

```bash
sudo apt install \
  ros-humble-joint-state-publisher \
  ros-humble-xacro \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup -y
```

## セットアップ中に出たエラーと対処

### ① `colcon build` がメモリ不足で失敗する

Raspberry Pi 4 でそのままビルドするとメモリが足りずに止まることがある。

```bash
# NG: 並列ビルドがメモリを使い切る
colcon build --symlink-install

# OK: 並列数を絞る
colcon build --symlink-install --parallel-workers 2
```

### ② `odom_manager` が起動直後にクラッシュする

`nav_base.launch.py` を起動すると `odom_manager` が即クラッシュした。

```
[ERROR] [odom_manager_node]: ModuleNotFoundError: No module named 'tf_transformations'
```

原因は `tf_transformations` パッケージの不足。以下で解決した。

```bash
sudo apt install ros-humble-tf-transformations -y
pip install transforms3d
```

### ④ LiDAR の CheckSum エラーが大量に出る

```
[error] Check Sum 0x7282 != 0x7A6E
[ERROR] Failed to get scan
```

SLAM 起動時にこのエラーが大量に出続けることがある。壊れているように見えるが、実際にスキャンデータが流れているか確認する。

```bash
ros2 topic hz /scan
# → average rate: 11.5
```

11Hz 以上出ていれば問題なく動作している。slam_toolbox は欠損スキャンに比較的強く、地図作成は問題なく進む。エラーログよりトピックの実態で判断する。

### ⑤ ゲームパッドが認識されない

```
[ERROR] Failed to open joystick: /dev/input/js0
```

デバイスパスが違う場合がある。まず確認する。

```bash
ls /dev/input/js*
```

`js1` や `js2` が出た場合は、launch ファイル内の `/dev/input/js0` をその値に書き換える。

### ③ I2C デバイスにアクセスできない

```
[ERROR] Permission denied: '/dev/i2c-1'
```

起動のたびに以下が必要だった。

```bash
sudo chmod 666 /dev/i2c-*
```

再起動後も有効にしたい場合は udev ルールを設定する。

```bash
sudo tee /etc/udev/rules.d/99-lightrover.rules << 'EOF'
KERNEL=="i2c-*", MODE="0666"
KERNEL=="ttyUSB*", MODE="0666"
EOF
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## 参考リンク

- [ライトローバー公式 WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
- [公式セットアップ手順](https://vstoneofficial.github.io/lightrover_webdoc/setup/softwareSetupUbuntuRos2_humble/)
- [lightrover-workspace リポジトリ](https://github.com/t0k0shi/lightrover-workspace)
