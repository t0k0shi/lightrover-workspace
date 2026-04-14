# Lightrover テレメトリダッシュボード

Lightrover の走行データ（速度・位置・軌跡）をリアルタイムで可視化するシステムです。
InfluxDB 2.7 + Grafana 10.4 を Docker Compose で一括起動し、ROS2 の `/odom`・`/cmd_vel` トピックをブラウザで可視化します。

```
Lightrover (ROS2 Humble)
  └─ /odom, /cmd_vel
       │  Wi-Fi（マルチキャスト通過設定必須）
       ▼
講師PC: Bridgeノード → InfluxDB 2.7 → Grafana 10.4
                                            │ http://<講師PC IP>:3000
                                            ▼
                               受講者PC（最大20台）ブラウザで閲覧
```

## 前提条件

| 項目 | 要件 |
|------|------|
| OS | Ubuntu 22.04 / macOS / Windows (WSL2) |
| Docker | 20.10 以上 |
| Docker Compose | v2 以上（`docker compose` コマンド） |
| ROS2 | Humble（Bridgeノード起動時のみ） |
| Python | 3.10 以上（Bridgeノード・Power BIエクスポート用） |
| ネットワーク | Wi-Fi でロボットと同一セグメント、**社内OA網に非接続** |

## セットアップ手順

### ステップ 1: リポジトリをクローンして telemetry ディレクトリへ移動

```bash
git clone https://github.com/t0k0shi/lightrover-workspace.git
cd lightrover-workspace/telemetry
```

### ステップ 2: 環境変数ファイルを作成する

```bash
cp .env.example .env
```

`.env` を編集してパスワードとトークンを設定します（**セミナー前に必ず変更すること**）。

```bash
# .env の編集例
INFLUXDB_ADMIN_PASSWORD=your-secure-password
INFLUXDB_TOKEN=your-secure-token-32chars-or-more
GRAFANA_ADMIN_PASSWORD=your-secure-password
```

> **セキュリティ注意:** `.env` は `.gitignore` で除外済みです。リポジトリにコミットしないでください。

### ステップ 3: Docker Compose を起動する

```bash
docker compose up -d
```

初回起動時は InfluxDB・Grafana のイメージをダウンロードするため数分かかります。

起動確認:

```bash
docker compose ps
# lightrover_influxdb ... (healthy)
# lightrover_grafana  ... Up
```

- Grafana: `http://localhost:3000`（匿名アクセス可・ログイン不要）
- InfluxDB: `http://localhost:8086`

### ステップ 4: Bridgeノードを起動する（ROS2 環境が必要）

```bash
# ROS2 環境をソース
source /opt/ros/humble/setup.bash

# 依存ライブラリをインストール
pip install -r bridge/requirements.txt

# Bridgeノードを起動
INFLUXDB_TOKEN=your-secure-token-32chars-or-more \
INFLUXDB_URL=http://localhost:8086 \
python3 bridge/telemetry_bridge.py
```

起動後、ログに以下が表示されたらサブスクリプション成立:

```
[INFO] Subscribed: /odom, /cmd_vel
```

### ステップ 5: Lightroverを走行させてダッシュボードを確認する

1. `teleop_twist_keyboard` でロボットを操作する
2. ブラウザで `http://<講師PC IP>:3000` を開く
3. 速度・軌跡パネルにデータが表示されることを確認する

---

## セミナー当日の運用手順

### 開始前（10分前を目安）

```bash
# 1. コンテナ起動確認
docker compose ps

# 2. 起動していなければ起動
docker compose up -d

# 3. ブラウザで動作確認（講師PC）
# → http://localhost:3000 でダッシュボードが表示されること

# 4. Bridgeノード起動
INFLUXDB_TOKEN=... python3 bridge/telemetry_bridge.py &

# 5. テスト走行でデータが流れることを確認
```

### セミナー終了後

```bash
# コンテナを停止する（データは保持される）
docker compose down

# データも削除する場合（次回セミナーまでに走行ログが不要な場合）
docker compose down -v
```

> **注意:** `-v` オプションを付けると InfluxDB の走行データも削除されます。事後分析に使う場合は付けないでください。

---

## ダッシュボードパネル一覧

| パネル | タイプ | 内容 |
|--------|--------|------|
| P1 速度: 指令 vs 実測 | 時系列 | linear.x の指令値（赤点線）と実測値（ティール実線）の比較 |
| P2 角速度: 指令 vs 実測 | 時系列 | angular.z の指令値と実測値の比較 |
| P3 現在速度 | ゲージ | 0〜0.6 m/s（0.4 m/s で色変化） |
| P4 現在角速度 | ゲージ | -2.0〜2.0 rad/s |
| P5 ロボット姿勢 | ゲージ | yaw 角 -180°〜180° |
| P6 走行軌跡 | XY Chart | pos_x / pos_y の 2D 散布図 |
| P7 総走行距離 | Stat | 速度の時間積分による累積距離（m） |
| P8 位置 X/Y 時系列 | 時系列 | pos_x・pos_y の時間変化 |

> **オドメトリドリフトについて:** `pos_x`・`pos_y` はホイールエンコーダの積分値（デッドレコニング）のため、走行時間に比例して誤差が蓄積します。閉ループルートを走行しても軌跡が「閉じない」現象が起きますが、これはバグではありません。SLAMとの違いを説明する教材として活用してください。

---

## トラブルシューティング

### データがダッシュボードに表示されない

```bash
# 1. Bridgeノードが起動しているか確認
ps aux | grep telemetry_bridge

# 2. /odom が配信されているか確認
ros2 topic hz /odom   # 10 Hz 以上なら OK

# 3. InfluxDB に書き込まれているか確認
curl -s -H "Authorization: Token <your-token>" \
  "http://localhost:8086/api/v2/query?org=lightrover" \
  --data 'from(bucket:"seminar") |> range(start: -1m) |> limit(n:1)'
```

### Grafana にアクセスできない（受講者PC）

```bash
# 講師PCのIPアドレスを確認
ip addr show | grep "inet "

# 講師PCのファイアウォールでポート3000を開放
sudo ufw allow 3000/tcp
```

### Grafana の XY Chart パネルが表示されない

XY Chart は Grafana 10.4.0 以上が必要です。バージョンを確認してください。

```bash
docker exec lightrover_grafana grafana-cli --version
```

### docker compose up でエラーが出る

```bash
# ポートが使用中の場合
ss -tlnp | grep -E ':3000|:8086'
# 使用中のプロセスを確認して停止するか、docker-compose.yml のポートを変更する
```

---

## ディレクトリ構成

```
telemetry/
├── docker-compose.yml        # InfluxDB + Grafana 一括起動
├── .env.example              # 環境変数テンプレート（.env は gitignore 済み）
├── README.md                 # このファイル
├── bridge/
│   ├── telemetry_bridge.py   # ROS2 /odom,/cmd_vel → InfluxDB Bridgeノード
│   └── requirements.txt
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/influxdb.yml   # InfluxDB データソース自動登録
│   │   └── dashboards/default.yml    # ダッシュボード自動ロード設定
│   └── dashboards/
│       └── lightrover.json           # 8パネルダッシュボード定義
└── powerbi/
    ├── export_for_powerbi.py         # CSV/Parquet エクスポート
    ├── powerbi_guide.md              # Power BI 連携手順
    └── lightrover_theme.json         # Power BI テーマ（Grafana 配色統一）
```

---

## セキュリティ注意事項

- **社内OA網への非接続:** `GF_AUTH_ANONYMOUS_ENABLED=true` のため、社内ネットワークに接続した状態でこのシステムを起動しないでください。セミナー会場のWi-Fiのみに接続して使用してください。
- **パスワード管理:** `.env` のデフォルト値はサンプルです。セミナー前に必ず変更してください。`.env.example` のパスワードをそのまま使わないでください。
- **セミナー終了後:** `docker compose down` でコンテナを停止し、不要な場合はネットワーク開放を閉じてください。
- **microSD:** Raspberry Pi 4 の microSD には OS と走行ログが含まれます。紛失・廃棄時は情シス規程に従ってください。

---

## 参考資料

| リソース | URL |
|---------|-----|
| Lightrover WebDoc | https://vstoneofficial.github.io/lightrover_webdoc/ |
| InfluxDB 2.7 ドキュメント | https://docs.influxdata.com/influxdb/v2.7/ |
| Grafana 10.4 ドキュメント | https://grafana.com/docs/grafana/v10.4/ |
| 要件定義書 | `../docs/specs/lightrover-seminar/telemetry-requirements.md` |
| 設計書 | `../docs/specs/lightrover-seminar/design.md` |
