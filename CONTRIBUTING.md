# CONTRIBUTING

lightrover-workspace への貢献を歓迎します。

## 開発環境のセットアップ

```bash
git clone https://github.com/t0k0shi/lightrover-workspace.git
cd lightrover-workspace
pip install pre-commit
pre-commit install
```

## 貢献の流れ

### 1. Issue で宣言する

着手前に Issue を立て、コメントで「対応します」と宣言してください。
他の方と作業が重複するのを防ぎます。

### 2. ブランチを作成する

```bash
git checkout -b feature/issue-XXX-短い説明
```

### 3. 変更を実装する

変更後、ローカルで lint を通してください:

```bash
pre-commit run --all-files
```

### 4. PR を作成する

PR テンプレート（`.github/PULL_REQUEST_TEMPLATE.md`）に沿って記入してください。

## ルール

| # | ルール | 詳細 |
|---|--------|------|
| 1 | PR の前に Issue で宣言 | 着手前に Issue を立て、コメントで「対応します」と宣言する |
| 2 | 1PR = 1スコープ | 複数の独立した変更を1つの PR に混在させない |
| 3 | 新コード = 新テスト | コード追加時は必ず対応するテストを追加する |
| 4 | CI グリーン必須 | lint.yml が PASS するまでマージ不可 |
| 5 | pre-commit で lint 通す | push 前にローカルで `pre-commit run --all-files` を実行する |
| 6 | コミットメッセージに対象パス | `src/lightrover_nav2/: ウェイポイント追従 launch を追加` 形式 |
| 7 | レビュー 1週間 SLO | PR を開いてから 1週間以内にレビュー着手する |
| 8 | カバレッジを下げない | 既存テストのカバレッジ率を維持すること |
| 9 | good first issue ラベル活用 | 初心者向けタスクには `good first issue` ラベルを付与する |

## コミットメッセージ規則

```
<対象パス>: <変更内容の要約>

例:
src/lightrover_ros/: bringup launch にパラメータ引数を追加
ci: lint.yml に ament_lint_cmake を追加
docs: hardware-checklist に SLAM 手順を追記
```

## SLO 定義

| 項目 | 目標 |
|------|------|
| レビュー開始 | PR 作成後 1週間以内 |
| マージ判断 | レビュー開始後 2週間以内 |

## upstream（vstoneofficial/lightrover_ros2）との同期

本リポジトリは [vstoneofficial/lightrover_ros2](https://github.com/vstoneofficial/lightrover_ros2) を fork して `src/` に直接配置しています（ADR-001 参照）。

upstream の変更を取り込む場合:

```bash
git remote add upstream https://github.com/vstoneofficial/lightrover_ros2.git
git fetch upstream
git diff upstream/humble -- src/lightrover_ros/
# 差分を確認してから手動マージ
```

定期的に upstream の更新を確認してください。

## スコープ外

以下は将来の Issue として切り出す予定です:

- Foxglove Bridge を用いた可視化環境
- テレメトリパイプライン（ライトローバー → InfluxDB → Grafana）
