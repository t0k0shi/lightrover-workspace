---
marp: true
theme: default
paginate: true
header: "ROS2ではじめるロボット開発入門"
footer: "第2回：実機を動かしてみる"
---

# 第2回：実機を動かしてみる

**ゴール：実機ロボットを動かし、RViz2でデータの流れを体感する**

所要時間：約3時間

---

## 前回の復習

| 用語 | 意味 |
|------|------|
| **ノード** | 役割を持つプログラム |
| **トピック** | ノード間の通信チャンネル |
| **Publish** | データを送信する |
| **Subscribe** | データを受信する |

### 今日の確認

```bash
export ROS_DOMAIN_ID=1
ros2 topic list
```

トピックが見えたらOK！

---

## 本日の構成

```
0:00  前回復習・環境確認
0:15  実機 bringup デモ
0:35  キーボード操作デモ
0:55  RViz2でトピックを見る
1:10  ── 休憩 ──
1:20  SLAMデモ（地図作成）
1:50  地図の保存
2:10  ROS2アーキテクチャ解説
2:30  質疑応答
2:45  まとめ・次回予告
```

---

## 実機 bringup：起動するノード

```bash
# デバイス権限設定
sudo chmod 666 /dev/i2c-*

# 基本 bringup
ros2 launch lightrover_ros nav_base.launch.py
```

### 起動するノード

| ノード | 役割 |
|--------|------|
| `ydlidar_ros2_driver_node` | YDLiDAR X2 からスキャンデータを取得 |
| `i2c_controller_node` | VS-WRC201 制御基板との通信 |
| `odom_manager_node` | エンコーダーから位置を計算 |
| `pos_controller_node` | 速度指令を受けてモーターを制御 |

---

## 実機 bringup：トピックを確認

```bash
# 別ターミナルで実行
ros2 node list
ros2 topic list
```

### 確認すべきトピック

```
/scan          ← LiDARスキャンデータ
/odom          ← ロボットの位置・速度
/rover_twist   ← 速度指令（入力）
/tf            ← 座標変換
```

---

## キーボード操作デモ

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args --remap cmd_vel:=/rover_twist
```

| キー | 動作 |
|------|------|
| `i` | 前進 |
| `k` | 停止 |
| `j` | 左回転 |
| `l` | 右回転 |
| `u` / `o` | 斜め前進 |

---

## キーボード操作中のデータを見る

操作しながら別ターミナルで確認：

```bash
# 速度指令の中身を見る
ros2 topic echo /rover_twist

# オドメトリの中身を見る
ros2 topic echo /odom

# 配信レートを確認
ros2 topic hz /odom
```

→ キーを押すたびに `/rover_twist` の値が変わる様子を確認

---

## RViz2 でトピックを可視化

```bash
rviz2
```

### 表示する設定

1. 左パネル「Add」→ 以下を追加：
   - **LaserScan** → Topic: `/scan`
   - **Odometry** → Topic: `/odom`
   - **TF** → （自動表示）

2. Fixed Frame を `odom` に変更

→ LiDARの点群とロボットの軌跡がリアルタイムで表示される

---

## 休憩（10分）

---

## SLAM とは？

> **S**imultaneous **L**ocalization **A**nd **M**apping
> 「自己位置推定と地図作成を同時に行う技術」

```
ロボットが動く → LiDARでスキャン
    ↓
「今どこにいるか？」を推定しながら
「周りはどんな形か？」を記録
    ↓
2D 地図が出来上がる
```

掃除ロボットが部屋の形を覚えるのと同じ仕組み

---

## SLAM デモ：起動手順

### ターミナル1（nav_base）
```bash
sudo chmod 666 /dev/i2c-*
ros2 launch lightrover_ros nav_base.launch.py
```

### ターミナル2（SLAM）
```bash
ros2 launch lightrover_ros lightrover_slam.launch.py
```

### ターミナル3（teleop）
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args --remap cmd_vel:=/rover_twist
```

---

## SLAM デモ：地図が育つ様子を見る

```bash
# 地図の配信レートを確認（1Hzで更新されていればOK）
ros2 topic hz /map
```

### RViz2 で地図を可視化

「Add」→ **Map** → Topic: `/map`

→ ロボットが動くほど白い領域が広がる

---

## 地図の保存

地図作成が完了したら保存：

```bash
ros2 run nav2_map_server map_saver_cli \
  -f ~/ros2_ws/src/lightrover_ros2/lightrover_navigation/maps/my_map
```

### 生成されるファイル

| ファイル | 内容 |
|---------|------|
| `my_map.pgm` | 地図画像（白黒） |
| `my_map.yaml` | 解像度・原点などのメタデータ |

→ 第3回の自律走行でこの地図を使用

---

## ROS2 アーキテクチャ図

```
[teleop_keyboard]
    │ /rover_twist
    ▼
[pos_controller] ── I2C ──▶ [VS-WRC201] ──▶ モーター
    
[YDLiDAR X2]
    │ /scan
    ├──▶ [slam_toolbox] ──▶ /map
    └──▶ [RViz2]

[エンコーダー]
    │ /odom
    └──▶ [slam_toolbox]
```

---

## launch ファイルとは？

複数のノードをまとめて起動する設定ファイル

```python
# lightrover_ros/lightrover_ros/nav_base.launch.py（概念）

def generate_launch_description():
    return LaunchDescription([
        Node(package='ydlidar_ros2_driver', ...),   # LiDAR
        Node(package='lightrover_ros', executable='i2c_controller', ...),
        Node(package='lightrover_ros', executable='odom_manager', ...),
        Node(package='lightrover_ros', executable='pos_controller', ...),
    ])
```

→ `ros2 launch` 1コマンドで全ノードが起動

---

## 本日のまとめ

- ✅ `nav_base.launch.py` で4ノードが同時起動する
- ✅ `teleop_twist_keyboard` でロボットをキーボード操作できる
- ✅ `/scan`・`/odom` がリアルタイムに流れている
- ✅ SLAM で2D地図が作れる
- ✅ `map_saver_cli` で地図をファイルに保存できる

---

## 次回予告：第3回 自律走行＋テレメトリ可視化

- 保存した地図で **Nav2 自律走行**
- 走行データを **Grafana** でリアルタイム可視化
- 「速度の指令 vs 実測」をグラフで読む

**宿題：** `ros2 topic hz /odom` が確認できること

---

## 参考リンク

- [ライトローバー公式 WebDoc - SLAM](https://vstoneofficial.github.io/lightrover_webdoc/ros2_software_humble/slam/)
- [slam_toolbox GitHub](https://github.com/SteveMacenski/slam_toolbox)
- [RViz2 公式ドキュメント](https://docs.ros.org/en/humble/Tutorials/Intermediate/RViz/RViz-User-Guide/RViz-User-Guide.html)
