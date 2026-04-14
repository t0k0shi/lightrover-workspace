# Lightrover テレメトリダッシュボード

Lightrover の走行データ（速度・位置・軌跡）をリアルタイムで可視化するシステムです。

```
Lightrover (ROS2 Humble)
  └─ /odom, /cmd_vel
       │  Wi-Fi
       ▼
講師PC: Bridgeノード → InfluxDB 2.7 → Grafana 10.4
                                            │
                                            ▼
                               受講者PC（最大20台）ブラウザで閲覧
```

## クイックスタート

### 1. 環境変数を設定する

```bash
cp .env.example .env
# .env を編集してパスワード・トークンを設定する
```

### 2. Docker Compose を起動する

```bash
docker compose up -d
```

Grafana: http://localhost:3000（匿名アクセス可）
InfluxDB: http://localhost:8086

### 3. Bridgeノードを起動する

```bash
cd bridge
pip install -r requirements.txt
python3 telemetry_bridge.py
```

## ディレクトリ構成

```
telemetry/
├── docker-compose.yml        # InfluxDB + Grafana 一括起動
├── .env.example              # 環境変数テンプレート
├── README.md                 # このファイル
├── bridge/
│   ├── telemetry_bridge.py   # ROS2トピック → InfluxDB Bridgeノード
│   └── requirements.txt
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/      # InfluxDB データソース自動設定
│   │   └── dashboards/       # ダッシュボードプロバイダ設定
│   └── dashboards/
│       └── lightrover.json   # 8パネルダッシュボード定義
└── powerbi/
    ├── export_for_powerbi.py # CSV/Parquetエクスポート
    ├── powerbi_guide.md      # Power BI 連携手順
    └── lightrover_theme.json # Power BI テーマ
```

## 要件・設計

- 要件定義書: `docs/specs/lightrover-seminar/telemetry-requirements.md`
- 設計書: `docs/specs/lightrover-seminar/design.md`

## 注意事項

- `GF_AUTH_ANONYMOUS_ENABLED=true` のため、本システムは社内OA網に接続しない環境で使用すること
- 管理者パスワードはセミナー前に `.env` で変更すること
- セミナー終了後は `docker compose down` でコンテナを停止すること
