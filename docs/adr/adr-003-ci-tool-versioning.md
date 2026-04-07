# ADR-003: CI ツール バージョン管理方式

## メタデータ

| 項目 | 内容 |
|------|------|
| 日付 | 2026-04-07 |
| 状態 | 確定 |
| 対象 | lightrover-workspace lint 基盤 |

## コンテキスト

pre-commit（ローカル）と GitHub Actions（CI）で同じ lint ツール（yamllint, ruff, xmllint）を使用する。両者のバージョンが乖離すると「ローカルで通るが CI で落ちる」問題が発生する。

過去の教訓:
- 教訓 10: lint と format は別コマンド — 両方実行しないと CI で落ちる
- 教訓 13: rebase 後は lint + diff で結果を検証する

## 選択肢

### A. pre-commit のみバージョン固定

CI は latest を使用。ローカルとの乖離リスクあり。

### B. CI のみバージョン固定

ローカルは任意バージョン。開発者間の環境差異が発生。

### C. 両方独立にバージョン固定

2箇所でバージョンを管理。同期忘れのリスク。

### D. .pre-commit-config.yaml を SSOT

pre-commit の `rev:` を正とし、CI は `pre-commit run` で実行。バージョンが自動的に一致。

## 3 Agents Model 分析

**[Affirmative]**: D 方式なら `.pre-commit-config.yaml` の1ファイルを更新するだけで、ローカルと CI のバージョンが自動的に一致する。管理コスト最小。

**[Critical]**: CI で `pre-commit run` を使うと、pre-commit の仮想環境構築に時間がかかる。個別に `ruff check` 等を直接実行する方が速い場合がある。

**[Mediator]**: 実行時間はキャッシュで緩和可能（実測 45 秒）。バージョン乖離によるデバッグ時間の方がコストが高い。D を採用する。

## 決定

**D. .pre-commit-config.yaml を SSOT** とする。

CI の lint.yml は `pre-commit run --all-files` で実行し、ツールバージョンを `.pre-commit-config.yaml` から自動取得する。

## 運用手順

1. バージョンアップは `.pre-commit-config.yaml` の `rev:` を更新することから始める
2. CI は同じファイルを参照するため、自動的にバージョンが同期される
3. CONTRIBUTING.md にバージョンアップ手順を記載する

## リスクと緩和策

| リスク | 緩和策 |
|--------|--------|
| pre-commit 仮想環境の構築時間 | `actions/cache` で `~/.cache/pre-commit` をキャッシュ |
| pre-commit 自体のバージョン差異 | CI で `pip install pre-commit` のバージョンを固定することも検討 |
