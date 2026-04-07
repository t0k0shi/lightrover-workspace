# ADR-002: pull_request_target セキュリティ設計

## メタデータ

| 項目 | 内容 |
|------|------|
| 日付 | 2026-04-07 |
| 状態 | 確定 |
| 対象 | lightrover-workspace ai-review |

## コンテキスト

AI PR レビュー（ai-review.yml）で Claude API を呼び出すには `ANTHROPIC_API_KEY` が必要。フォーク PR でも動作させるために、GitHub Actions のイベント選択が必要。

## 選択肢

### A. pull_request イベント

- メリット: フォーク PR のコードがベースリポジトリのコンテキストで実行されない（安全）
- デメリット: フォーク PR では Secrets にアクセスできず、API 呼び出しが失敗する

### B. pull_request_target イベント

- メリット: ベースリポジトリの Secrets にアクセス可能（フォーク PR でも動作）
- デメリット: 悪意あるフォーク PR がコードを改ざんして Secrets を流出させるリスク

## 3 Agents Model 分析

**[Affirmative]**: pull_request_target を使えば全 PR で AI レビューが動作し、コントリビューター体験が向上する。

**[Critical]**: フォーク PR で悪意あるコードが `scripts/review_pr.py` を改ざんし、ANTHROPIC_API_KEY を外部に送信する TOCTOU 攻撃のリスクがある。

**[Mediator]**: 緩和策を3重に講じることでリスクを許容範囲に抑える。学習リポジトリという性質上、高価値の Secrets は API キーのみであり、漏洩時の影響も限定的（キーのローテーションで対処可能）。

## 決定

**B. pull_request_target** を採用する。

## 緩和策

| # | 緩和策 | 効果 |
|---|--------|------|
| 1 | `actions/checkout` で merge commit を指定 | フォークの HEAD を直接 checkout しない |
| 2 | `scripts/review_pr.py` は `ANTHROPIC_API_KEY` のみにアクセス | 他の Secrets への影響を排除 |
| 3 | ワークフロー自体は main ブランチのものが実行される | フォークがワークフローを改ざんできない |

## 監視

- GitHub Actions のログを定期確認し、キー漏洩の兆候がないか確認
- Anthropic Console でコスト異常がないか監視
- 漏洩が疑われる場合は即座に API キーをローテーション
