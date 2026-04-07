# lightrover-workspace

Vstone ライトローバー（ROS2 学習用小型ロボット）の開発ワークスペース。
セットアップ手順、CI/CD パイプライン、AI PR レビューを含む統合環境です。

## ハードウェア構成

| コンポーネント | 詳細 |
|--------------|------|
| ロボット本体 | Vstone ライトローバー |
| ボードPC | Raspberry Pi |
| OS | Ubuntu MATE 22.04 |
| LiDAR | YDLiDAR X2 |

## 前提条件

- Ubuntu MATE 22.04 (Raspberry Pi)
- ROS 2 Humble
- Python 3.10

## セットアップ手順

### 1. リポジトリのクローン

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/t0k0shi/lightrover-workspace.git
```

### 2. ROS2 環境の準備

詳細は [docs/setup/hardware-checklist.md](docs/setup/hardware-checklist.md) を参照してください。

### 3. ビルド

```bash
cd ~/ros2_ws
colcon build --symlink-install --cmake-clean-cache --parallel-workers 2
```

### 4. 動作確認

[セットアップ完了後に記載予定]

## ディレクトリ構造

```
lightrover-workspace/
├── .github/workflows/     # CI/CD パイプライン
├── docs/setup/            # 実機セットアップ手順
├── src/
│   ├── lightrover_ros/         # 本体制御パッケージ
│   ├── lightrover_description/ # URDF / meshes
│   └── lightrover_nav2/        # Nav2 / SLAM 統合
├── scripts/               # ユーティリティスクリプト
├── .pre-commit-config.yaml
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## CI/CD パイプライン

[Step 3 完了後に記載予定]

## CI がカバーする範囲

| 範囲 | CI で検証可否 | 検証方法 |
|------|-------------|---------|
| src/ の Python lint | 可 | GitHub Actions (lint.yml) |
| CMakeLists の lint | 可 | GitHub Actions (lint.yml) |
| 実機での colcon build | 不可（実機必須） | hardware-checklist.md |
| ROS2 トピック確認 | 不可（実機必須） | hardware-checklist.md |
| YDLiDAR スキャン確認 | 不可（実機必須） | hardware-checklist.md |

## ライセンス

[MIT License](LICENSE)

## 関連リンク

- [公式 ROS2 パッケージ](https://github.com/vstoneofficial/lightrover_ros2)
- [公式 WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
