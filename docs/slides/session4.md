---
marp: true
theme: default
paginate: true
header: "ROS2ではじめるロボット開発入門"
footer: "第4回：AI駆動開発と自動PRレビュー（発展編）"
---

# 第4回：AI駆動開発と自動PRレビュー

**ゴール：ロボットソフトウェアのCI/CD・AI自動レビューを自分の手で体験し、チーム開発の基礎を習得する**

所要時間：約2.5時間

---

## なぜロボットソフトにCI/CDが必要か？

### 人間だけのレビューの問題

```
開発者A が launch ファイルを変更
    ↓
レビュアーB がコードを見る
    ↓
「動作確認は？」「テストは？」「コーディング規約は？」
    ↓
実機で確認... ← 時間がかかる
```

→ **CI/CD + AI レビューで自動化できる部分がある**

---

## `lightrover-workspace` の CI/CD 構成

| コンポーネント | 役割 |
|--------------|------|
| `.github/workflows/lint.yml` | コード品質の自動チェック |
| `.github/workflows/ai-review.yml` | Claude API による自動レビュー |
| `scripts/review_pr.py` | diff → Claude API → PR コメント |
| `.pre-commit-config.yaml` | ローカル lint フック |
| `CONTRIBUTING.md` | 9つのPRルール・SLO定義 |

---

## lint.yml：自動チェックの内容

```yaml
# PR を出すと自動実行される
jobs:
  lint:
    steps:
      - yamllint      # YAML の構文・スタイル
      - ruff check    # Python lint（未使用import等）
      - ruff format   # Python フォーマット
      - xmllint       # XML/launch ファイルの構文
```

→ コードを push するたびに自動実行
→ 問題があれば PR の「✗」で即座にわかる

---

## CONTRIBUTING.md を読む

```
cat CONTRIBUTING.md
```

### 9つのPRルール（抜粋）

1. PR は1つの目的に絞る
2. コミットメッセージは `type: 概要` 形式
3. テストなし実装は禁止
4. ドキュメントと実装は同時更新
5. レビュー前にセルフチェック必須
...

---

## ディスカッション：ルールがないと何が起きるか？

**「このルールがないと何が起きるか？」**

例：
- PR が大きすぎる → レビューに時間がかかる
- コミットメッセージが曖昧 → 履歴を追えない
- テストなし → 本番で初めてバグが発覚

→ **ルールはチームを守るためにある**

---

## 休憩（10分）

---

## pre-commit をローカルで試す

```bash
# インストール
pip install pre-commit
pre-commit install

# 意図的に lint 違反を作る
echo "import os" >> scripts/test_lint.py

# コミットしてみる
git add scripts/test_lint.py
git commit -m "test: lint 違反テスト"
```

→ pre-commit が**ブロック**して、コミットできない！

---

## pre-commit の動作

```
git commit 実行
    ↓
pre-commit フックが起動
    ├── yamllint: YAML ファイルをチェック
    ├── ruff: Python をチェック
    └── ruff-format: Python フォーマットをチェック
            ↓
        違反があれば自動修正 or エラー表示
            ↓
        コミット中断（再度 add → commit が必要）
```

→ **push する前に問題を発見できる**

---

## GitHub Actions で CI を見る

GitHub の PR ページで確認：

```
Checks タブ
    ├── ✅ yamllint        passed
    ├── ✅ ruff            passed
    ├── ✅ ruff-format     passed
    └── 🤖 ai-review      コメントを投稿
```

→ 全て ✅ になるまでマージできない設定

---

## AI 自動レビューの仕組み

```python
# scripts/review_pr.py（概念）

# 1. PR の diff を取得
diff = get_pr_diff(pr_number)

# 2. Claude API に送信
response = claude.messages.create(
    model="claude-sonnet-4-6",
    messages=[{"role": "user",
               "content": f"このdiffをレビューしてください:\n{diff}"}]
)

# 3. PR にコメントを投稿
post_pr_comment(pr_number, response.content)
```

---

## AI レビューコメントの読み方

### 良い指摘の例

```
⚠️ Warning: `i2c_address` がハードコードされています。
設定ファイルまたは launch パラメータで外部化することを推奨します。
```

### 無視してよい例

```
💡 Info: 変数名 `x` は意図が不明です。
→ ROS の標準メッセージフィールド名なので変更不要
```

**→ 全指摘に対応する必要はない。スコープと文脈で判断する**

---

## ハンズオン：PR を出して AI レビューを受ける

### 手順

```bash
# 1. リポジトリを Fork（GitHub 上で）
# 2. Fork したリポジトリをクローン
git clone https://github.com/<あなたのID>/lightrover-workspace.git

# 3. ブランチを作成
git checkout -b feat/my-first-pr

# 4. 小さな変更を加える（例：コメントを追加）
# 5. コミット・push
git commit -m "docs: コメント追加"
git push origin feat/my-first-pr

# 6. PR を作成（GitHub 上で）
```

---

## AI レビューが届くまで待つ

GitHub Actions が完了するまで約1〜2分

```
PR を作成
    ↓
GitHub Actions トリガー
    ↓
ai-review.yml が実行
    ↓
Claude API が diff を解析
    ↓
PR に自動コメントが投稿される 🤖
```

---

## グループワーク：AI レビューを評価する

届いたコメントを見て議論：

1. **対応すべき指摘**はどれか？
2. **無視してよい指摘**はどれか？（理由も）
3. AI レビューで**気づかなかった問題**が見つかったか？
4. AI レビューの**限界**は何か？

---

## ディスカッション（10分）

### テーマ

- AI レビューで何が変わるか？
- 誤検知にどう対応するか？
- 自分のチームに導入するとしたら？

---

## まとめ：CI/CD + AI レビューの価値

| 従来 | CI/CD + AI レビュー |
|------|-------------------|
| 人間が全てチェック | lint は自動化 |
| レビューに時間がかかる | AI が即座に指摘 |
| 指摘の漏れがある | 網羅的なチェック |
| ルールが曖昧 | CONTRIBUTING.md で明文化 |

→ **人間はより重要な判断に集中できる**

---

## 本日のまとめ

- ✅ pre-commit でローカル lint を体験した
- ✅ GitHub Actions の CI ワークフローを理解した
- ✅ AI レビューの仕組みと読み方を学んだ
- ✅ PR を作成して AI レビューを受けた
- ✅ 「対応すべき指摘」「無視してよい指摘」を判断できる

---

## 全4回の振り返り

| 回 | 達成したこと |
|----|------------|
| 第1回 | ROS2の世界観・ノード・トピックを理解 |
| 第2回 | 実機操作・SLAM で地図作成 |
| 第3回 | 自律走行・テレメトリ可視化 |
| **第4回** | **CI/CD・AI レビューによるチーム開発** |

---

## 次のステップ

### 自学リソース

- [ROS2 公式チュートリアル](https://docs.ros.org/en/humble/Tutorials.html)
- [ライトローバー WebDoc](https://vstoneofficial.github.io/lightrover_webdoc/)
- [Nav2 公式ドキュメント](https://navigation.ros.org/)
- [GitHub Actions 公式](https://docs.github.com/ja/actions)
- [Anthropic API 公式](https://docs.anthropic.com/)
- [lightrover-workspace リポジトリ](https://github.com/t0k0shi/lightrover-workspace)

---

## ありがとうございました！

受講後アンケートへのご協力をお願いします。

```
第1回〜第4回を通じて
「ROS2ロボットをチームで開発・維持できる」
ベースラインを習得しました。
```

**引き続き lightrover-workspace で実験してみてください！**
