# ADR-001: lightrover_ros2 の取り込み方式

## メタデータ

| 項目 | 内容 |
|------|------|
| 日付 | 2026-04-07 |
| 状態 | 確定 |
| 対象 | lightrover-workspace |

## コンテキスト

公式パッケージ vstoneofficial/lightrover_ros2 を本リポジトリにどう取り込むかを決定する必要がある。CI でのビルド容易性、ブログ記事での説明しやすさ、upstream 追従のコストが判断基準。

## 選択肢

### A. git submodule

upstream をサブモジュールとして参照する。`git clone --recursive` で取得。

- メリット: upstream の変更を `git submodule update` で追従可能
- デメリット: 初心者には `--recursive` を忘れやすく、チェックアウト失敗に気づきにくい

### B. fork + src/ 直接配置

upstream を fork し、src/ に直接コードを配置する。

- メリット: CI で `colcon build` がシンプル、ブログ記事の説明が容易
- デメリット: upstream の修正を手動マージする必要がある

### C. fork + sparse-checkout

upstream の一部ディレクトリだけを取り込む。

- メリット: 必要なパッケージだけを選択可能
- デメリット: 現時点でパッケージの一部だけ使う必要がなく、オーバーエンジニアリング

## 3 Agents Model 分析

**[Affirmative]**: fork + 直接配置は CI シンプル化とブログ説明容易性の両面で最適。単一リポジトリで完結するため読者が迷わない。

**[Critical]**: upstream の修正（バグフィックス等）を取り込む際に手動マージが必要。乖離が大きくなるとコンフリクト解決コストが高い。

**[Mediator]**: 本プロジェクトは「学習環境の整備」が目的であり、upstream 追従頻度は低い。fork + 直接配置を採用し、CONTRIBUTING.md に定期的な upstream 確認手順を記載して緩和する。

## 決定

**B. fork + src/ 直接配置** を採用する。

## 採用しなかった選択肢

- **git submodule**: 初心者に `--recursive` clone が必要で、README の説明が複雑化する
- **sparse-checkout**: パッケージの一部だけ使う必要が現時点ではなく、不要な複雑さ

## リスクと緩和策

| リスク | 緩和策 |
|--------|--------|
| upstream との乖離 | CONTRIBUTING.md に定期確認手順を記載 |
| ライセンス互換性 | 実装時に upstream の LICENSE を確認（MIT と Apache-2.0 は互換） |
