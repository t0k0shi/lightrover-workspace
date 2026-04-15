---
marp: true
theme: default
paginate: true
header: "ROS2ではじめるロボット開発入門"
footer: "第3回：自律走行とテレメトリ可視化"
---

# 第3回：自律走行とテレメトリ可視化

**ゴール：自律走行の仕組みとテレメトリダッシュボードを理解し、業務への接点を考える**

所要時間：約3時間

---

## 前回の復習

- SLAM で地図を作成・保存した（`my_map.pgm` / `my_map.yaml`）
- `/scan`・`/odom` の意味を理解した
- RViz2 でトピックを可視化した

### 今日やること

```
自律走行（Nav2）でロボットが自分で動く
    ↓
走行データを Grafana でリアルタイム可視化
    ↓
「速度の指令 vs 実測」を読み解く
```

---

## Nav2 とは？

**Nav2 = ROS2 の自律ナビゲーションスタック**

```
[地図] + [現在位置] + [目標地点]
            ↓
    [経路計画（Planner）]
            ↓
    [障害物回避（Controller）]
            ↓
    [速度指令 /rover_twist]
            ↓
        ロボットが動く
```

→ 人間が何もしなくても目的地まで走れる

---

## 自律走行の起動手順

### ターミナル1（nav_base）
```bash
sudo chmod 666 /dev/i2c-*
ros2 launch lightrover_ros nav_base.launch.py
```

### ターミナル2（Nav2 + RViz2）
```bash
ros2 launch lightrover_navigation lightrover_navigation.launch.py \
  map:=/home/pi/ros2_ws/src/lightrover_ros2/lightrover_navigation/maps/my_map.yaml
```

---

## RViz2 で自律走行を操作

### 手順

1. 「**2D Pose Estimate**」をクリック
   → 地図上でロボットの現在位置をクリック＆ドラッグ

2. 緑の矢印（パーティクル）が出ればOK

3. 「**2D Nav Goal**」をクリック
   → 目的地をクリック＆ドラッグ

4. ロボットが自動で走り始める！

---

## 自律走行中に何が起きているか

```
[AMCL] ← 地図 + /scan + /odom で「今どこにいるか？」を推定
    ↓ /amcl_pose
[Planner] ← 目標地点への経路を計算
    ↓ /plan
[Controller] ← 障害物を避けながら経路に追従
    ↓ /rover_twist
[ロボット]
```

→ RViz2 で経路（緑の線）がリアルタイムで表示される

---

## 休憩（10分）

---

## テレメトリとは？

> 離れた場所からデータを収集・監視する仕組み

```
ロボット（Raspberry Pi）
    │ /odom, /cmd_vel（ROS2トピック）
    ↓ Wi-Fi
[Bridge ノード] → InfluxDB（時系列DB）→ Grafana（可視化）
                                              │
                                    ブラウザで http://<IP>:3000
                                              ↓
                                    受講者PCで閲覧可能
```

---

## データパイプライン全体図

```
Raspberry Pi                  Azure VM / 講師PC
┌─────────────────┐           ┌──────────────────────┐
│  ROS2 Humble    │           │  Docker Compose       │
│                 │           │                        │
│  /odom ──────── │──Wi-Fi──▶│  Bridge ──▶ InfluxDB  │
│  /cmd_vel ───── │──────────▶│                ↓      │
│                 │           │           Grafana :3000│
└─────────────────┘           └──────────────────────┘
```

---

## Grafana ダッシュボード：パネル一覧

| パネル | 内容 |
|--------|------|
| P1 速度：指令 vs 実測 | `linear.x` の指令値と実測値を比較 |
| P2 角速度：指令 vs 実測 | `angular.z` の比較 |
| P3 現在速度（ゲージ） | 0〜0.6 m/s |
| P4 現在角速度（ゲージ） | -2.0〜2.0 rad/s |
| P5 ロボット姿勢 | yaw 角 -180°〜180° |
| P6 走行軌跡 | XY 散布図 |
| P7 総走行距離 | 速度の時間積分（m） |
| P8 位置 X/Y 時系列 | pos_x・pos_y の時間変化 |

---

## Grafana の見方：速度グラフ

```
速度 (m/s)
  0.6 ┤
  0.4 ┤ ─ ─ 指令値（cmd_vel）
  0.2 ┤ ───── 実測値（odom）
  0.0 ┤──────────────────── 時間
```

- **指令値と実測値のズレ** = PID制御の追従性
- ズレが大きい → モーター応答が遅い / 路面が滑りやすい
- 自律走行時は Nav2 が自動で速度を調整する様子が見える

---

## Grafana の見方：走行軌跡

```
Y (m)
  1.0 ┤    ●
  0.5 ┤  ●   ●
  0.0 ┤●       ●
 -0.5 ┤  ●   ●
 -1.0 ┤    ●
      └──────────── X (m)
```

- XY Chart で2Dの移動軌跡を表示
- ホイールエンコーダの積分値（デッドレコニング）
- 長時間走行するとドリフト（誤差蓄積）が発生する

---

## ドリフトについて

> **オドメトリドリフト** = 走行時間とともに位置誤差が蓄積する現象

```
実際の経路:  ────────────────●
推定経路:    ─────────────────────●（ずれる）
```

**なぜ起きるか？**
- 車輪がスリップする
- エンコーダの分解能に限界がある
- 積分誤差が蓄積する

**SLAM との違い：** LiDARを使って地図と照合するため誤差が修正される

---

## ディスカッション（30分）

### テーマ：自分の業務でROS2をどう使うか？

考えるポイント：
- どんなロボット / 自動化機器が使えそうか？
- 今日見たテレメトリは何の監視に使えるか？
- データを可視化することで何が変わるか？

---

## 第4回への接続：AIとCI/CDの概観

### 「動いたコードをどうチームで守るか？」

```
git push
    ↓
GitHub Actions（CI）
    ├── yamllint / ruff（コード品質チェック）
    └── AI レビュー（Claude API）
            ↓
        PR に自動でコメントが投稿される
```

→ 人間がレビューする前に AI が問題を指摘

---

## クラウド連携の展望

| サービス | 用途 |
|---------|------|
| **Azure IoT Hub** | 複数台ロボットのデータ集約 |
| **Power BI** | 経営レポートへの可視化統合 |
| **Azure Monitor** | 異常検知・アラート |

→ 今日作ったパイプラインは業務システムへの接続口になる

---

## 本日のまとめ

- ✅ Nav2 で地図を使った自律走行ができる
- ✅ RViz2 で経路計画がリアルタイムで見える
- ✅ ROS2 → InfluxDB → Grafana のパイプラインを理解した
- ✅ 速度の「指令 vs 実測」からPID追従性を読み取れる
- ✅ ドリフトの原因と SLAM との違いを説明できる

---

## 次回予告：第4回 AI駆動開発（発展編）

- GitHub Actions の CI/CD を自分で体験
- AI 自動レビューを受けて修正するハンズオン
- `pre-commit` でローカル lint を体験

**準備：** GitHubアカウント、Python 3.10以上

---

## 参考リンク

- [ライトローバー公式 WebDoc - Nav2](https://vstoneofficial.github.io/lightrover_webdoc/ros2_software_humble/navigation/)
- [Nav2 公式ドキュメント](https://navigation.ros.org/)
- [InfluxDB 2.7 ドキュメント](https://docs.influxdata.com/influxdb/v2.7/)
- [Grafana 10.4 ドキュメント](https://grafana.com/docs/grafana/v10.4/)
- [lightrover-workspace リポジトリ](https://github.com/t0k0shi/lightrover-workspace)
