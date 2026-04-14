# Power BI 連携手順

Grafana で収集した Lightrover の走行データを Power BI Desktop で分析するための手順です。

## 前提条件

- Power BI Desktop（Windows）がインストール済み
- Python 3.10 以上 + pandas がインストール済み
- InfluxDB コンテナが起動中、またはエクスポート済みの CSV/Parquet ファイルがある

## ステップ 1: データをエクスポートする

講師 PC（InfluxDB が動作しているマシン）で以下を実行します。

```bash
cd lightrover-workspace/telemetry

# 直近7日分をCSVでエクスポート
INFLUXDB_TOKEN=<your-token> python3 powerbi/export_for_powerbi.py

# 期間を指定する場合
INFLUXDB_TOKEN=<your-token> python3 powerbi/export_for_powerbi.py \
  --start 2026-04-01 --end 2026-04-30

# Parquet形式で出力する場合（ファイルサイズが小さい）
INFLUXDB_TOKEN=<your-token> python3 powerbi/export_for_powerbi.py --format parquet
```

エクスポートされるファイル（`./export/YYYYMMDD/` に出力）:

| ファイル | 内容 | 粒度 |
|---------|------|------|
| `daily_summary.csv` | 日別走行サマリ | 1日 × ロボット |
| `run_sessions.csv` | 走行セッション一覧 | 1セッション × ロボット |
| `velocity_log.csv` | 速度ログ（指令 vs 実測） | 1秒 × ロボット |
| `trajectory.csv` | 走行軌跡 | 500ms × ロボット |

## ステップ 2: Power BI にデータを読み込む

1. Power BI Desktop を開く
2. **[データを取得]** → **[テキスト/CSV]** を選択
3. `export/YYYYMMDD/daily_summary.csv` を選択して **[読み込み]**
4. 同様に `run_sessions.csv`, `velocity_log.csv`, `trajectory.csv` を読み込む

> **Parquet の場合:** **[データを取得]** → **[Parquet]** を選択します。

## ステップ 3: テーマを適用する

Grafana と同じ配色にするためのテーマファイルを適用します。

1. **[表示]** → **[テーマ]** → **[テーマの参照]** をクリック
2. `powerbi/lightrover_theme.json` を選択
3. ダークテーマ（Grafana 風）が適用される

## ステップ 4: 推奨ビジュアル

### 走行サマリ（daily_summary テーブル）

| ビジュアル | X 軸 | Y 軸 | 用途 |
|-----------|------|------|------|
| 集合縦棒 | date | total_distance_m | 日別走行距離の比較 |
| 折れ線 | date | avg_speed_ms | 速度の推移 |
| カード | - | max_speed_ms の MAX | 期間中の最高速度 |

### 速度比較（velocity_log テーブル）

| ビジュアル | X 軸 | Y 軸 | 用途 |
|-----------|------|------|------|
| 折れ線 | timestamp | cmd_linear_x, odom_linear_x | 指令 vs 実測の追従性 |
| 散布図 | cmd_linear_x | odom_linear_x | 指令と実測の相関（理想は y=x） |

### 走行軌跡（trajectory テーブル）

| ビジュアル | X 軸 | Y 軸 | 用途 |
|-----------|------|------|------|
| 散布図 | pos_x | pos_y | 走行経路の可視化 |
| 折れ線 | timestamp | yaw_deg | 姿勢変化の時系列 |

## テーブル間のリレーション

Power BI のモデルビューで以下のリレーションを設定すると、フィルタが連動します。

```
daily_summary.robot_id ←→ run_sessions.robot_id
run_sessions.robot_id  ←→ velocity_log.robot_id
velocity_log.robot_id  ←→ trajectory.robot_id
```

## トラブルシューティング

### CSV の日本語が文字化けする

Power BI の CSV 読み込みで **[元のファイル]** → **[65001: Unicode (UTF-8)]** を選択してください。
エクスポートスクリプトは UTF-8 で出力します。

### Parquet が読み込めない

Power BI Desktop のバージョンが古い場合、Parquet 読み込みに対応していません。
2021年3月以降のバージョンを使用してください。

### データが空になる

エクスポートスクリプトの `--start` / `--end` の期間に走行データが存在するか確認してください。

```bash
# InfluxDB にデータがあるか確認
curl -s -H "Authorization: Token <your-token>" \
  "http://localhost:8086/api/v2/query?org=lightrover" \
  --data 'from(bucket:"seminar") |> range(start: -7d) |> limit(n:1)'
```
