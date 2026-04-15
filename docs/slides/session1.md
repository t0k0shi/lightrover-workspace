---
marp: true
theme: default
paginate: true
header: "ROS2ではじめるロボット開発入門"
footer: "第1回：ROS2の世界観をつかむ"
---

# ROS2ではじめるロボット開発入門

## 第1回：ROS2の世界観をつかむ

**— Lightrover × Grafana テレメトリダッシュボード × AI駆動開発 —**

---

## 本日のゴール

> ROS2が「何を解決するものか」を体感レベルで理解する

- ROS2のノード・トピック概念を人に説明できる
- `ros2 topic list` が自分のPCで通る
- ライトローバーの実機デモを見て「裏で何が流れているか」わかる

---

## 全4回の流れ

| 回 | テーマ | 内容 |
|----|--------|------|
| **第1回** | ROS2の世界観 | 今日はここ ← |
| 第2回 | 実機ハンズオン | teleop操作・SLAM地図作成 |
| 第3回 | 自律走行＋可視化 | Nav2・Grafanaダッシュボード |
| 第4回 | AI駆動開発 | CI/CD・AIレビュー（発展編） |

---

## なぜROSが生まれたか

### ロボット開発の昔の悩み

```
センサーA → 独自コード → モーターB
センサーA → また別のコード → モーターC
センサーA → さらに別のコード → アームD
```

→ **チームが変わるたびにゼロから書き直し**

---

## ROSが解決したこと

### 「ロボット版Slack」のイメージ

```
センサーA ──┐
センサーB ──┤  ROS（共通の通信基盤）  ├── モーター
センサーC ──┘                         └── カメラ
```

- 部品ごとに**独立したプログラム**（ノード）として作る
- ノード同士は**トピック**という共通の仕組みで会話する
- 誰が作ったコードでも**つなぎ合わせられる**

---

## ROS2の基本概念①：ノード

### ノード = ひとつの役割を持つプログラム

```
[LiDARノード]  → レーザーで周囲をスキャン
[ODOMノード]   → 車輪の回転から位置を計算
[CONTROLノード] → モーターに速度を指令
```

- 各ノードは**独立して動く**
- 止まっても他のノードは動き続ける
- 再利用・交換が簡単

---

## ROS2の基本概念②：トピック

### トピック = ノード間の「チャンネル」

```
[速度指令ノード] ──/rover_twist──→ [モータードライバー]
[LiDARノード]   ──/scan──────────→ [SLAMノード]
[ODOMノード]    ──/odom──────────→ [Navノード]
```

- トピック名は `/` から始まる（例：`/odom`）
- **Publish**（送信）と **Subscribe**（受信）
- 誰でも自由に購読できる

---

## ROS2の基本概念③：Pub/Sub

### メッセージの流れ

```
Publisher（送信側）        Subscriber（受信側）
     │                           │
     │ ── /scan ──────────────→  │
     │    （LiDARデータ）         │
```

- Publisher は「垂れ流す」だけ
- Subscriber は「聞きたいときに聞く」
- 1対多・多対1・多対多 すべてOK

---

## ここまでのまとめ

| 用語 | 意味 | 例 |
|------|------|-----|
| **ノード** | 役割を持つプログラム | LiDARドライバ、モーター制御 |
| **トピック** | ノード間の通信チャンネル | `/scan`, `/odom`, `/cmd_vel` |
| **Publish** | データを送信する | LiDARが測定値を送る |
| **Subscribe** | データを受信する | SLAMがスキャンデータを受け取る |

---

## 休憩（10分）

---

## ライトローバー紹介

### ハードウェア構成

| パーツ | 役割 |
|--------|------|
| **Raspberry Pi 4** | 頭脳（ROS2が動く） |
| **VS-WRC201** | 制御基板（モーター・I2C） |
| **YDLiDAR X2** | 目（レーザースキャナー） |
| **エンコーダー** | 足（車輪の回転を計測） |

---

## ライトローバーの内部構造

```
キーボード
    ↓ /rover_twist
[pos_controller]  ← 速度指令を受けてモーターを動かす
    ↓ I2C
[VS-WRC201基板]   ← 実際のモーター制御

[YDLiDAR X2]
    ↓ /scan
[slam_toolbox]    ← 地図を作る

[エンコーダー]
    ↓ /odom
[odom_manager]    ← 位置を計算する
```

---

## 実機デモ：起動してみる

### 実行するコマンド（講師PC）

```bash
# 1. デバイス権限設定
sudo chmod 666 /dev/i2c-*

# 2. 基本 bringup
ros2 launch lightrover_ros nav_base.launch.py
```

→ 起動するノード：
- `ydlidar_ros2_driver_node`（LiDAR）
- `i2c_controller_node`（制御基板）
- `odom_manager_node`（オドメトリ）
- `pos_controller_node`（速度制御）

---

## 実機デモ：トピックを見る

### 別ターミナルで実行

```bash
# 動いているノードの一覧
ros2 node list

# 配信中のトピック一覧
ros2 topic list

# odomの中身をリアルタイムで表示
ros2 topic echo /odom
```

→ ロボットが動いていなくても `/odom` は流れている

---

## 実機デモ：キーボードで操縦

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

→ 操作しながら `ros2 topic echo /rover_twist` を見てみよう

---

## 環境構築確認タイム（20分）

### 受講者のPCで確認

```bash
# ROS2 が入っているか確認
ros2 --version

# トピック一覧が見えるか確認
# ※ ROS_DOMAIN_ID を講師と合わせること
export ROS_DOMAIN_ID=1
ros2 topic list
```

✅ トピックが見えたら第2回の準備完了！

---

## 本日のまとめ

- ✅ ROSはロボット開発の「共通インフラ」
- ✅ ノード = 役割を持つプログラム
- ✅ トピック = ノード間の通信チャンネル
- ✅ Pub/Sub でデータを流す・受け取る
- ✅ `ros2 topic list` でリアルタイムに確認できる

---

## 次回予告：第2回 実機ハンズオン

- 実機を自分で操縦する（teleop）
- LiDARデータを RViz2 で可視化する
- **SLAM** で部屋の地図を作る
- 作った地図を保存する

**宿題：** `ros2 topic list` が自分のPCで動くことを確認しておく

---

## 参考リンク

- [ライトローバー公式 WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
- [ROS2 Humble 公式ドキュメント](https://docs.ros.org/en/humble/)
- [セットアップ手順書](https://github.com/t0k0shi/lightrover-workspace/blob/main/docs/setup/hardware-checklist.md)
