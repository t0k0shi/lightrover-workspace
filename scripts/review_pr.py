#!/usr/bin/env python3
"""AI PR review script using Claude API."""

import os
import sys

import anthropic

SYSTEM_PROMPT = """\
あなたは ROS 2 と Python に精通したコードレビュアーです。
以下の観点でコードレビューを行い、Critical な指摘のみを日本語で報告してください。

## レビュー観点（優先度順）

### P1: セキュリティ（必ず報告）
- API キー、パスワード、トークンのハードコード
- 任意コード実行につながるコマンドインジェクション

### P2: ROS2 固有の問題（重要な場合のみ報告）
- launch ファイルの引数とノードパラメータの名前不一致
- ノード名・トピック名の命名規則違反（snake_case の強制）
- QoS プロファイルの不整合（Publisher と Subscriber で一致しない）
- spin() / spin_once() の不適切な使用

### P3: Python コード品質（明らかなバグのみ報告）
- None チェックなしのメソッド呼び出し
- except 節での広すぎる例外捕捉

## 出力フォーマット

### コードレビュー

**Critical 指摘**: X 件

| 優先度 | ファイル | 行 | 指摘内容 | 推奨修正 |
|--------|---------|---|---------|---------|
| P1 | `src/...` | L42 | ... | ... |

（Critical 指摘がない場合は「問題なし」とだけ記載してください）

## ノイズ低減指示
- スタイルの好みに基づく指摘は行わないでください
- 既存コードの設計思想の変更提案は行わないでください
- この PR のスコープ外の改善提案は行わないでください
- すでに ruff が検出できる問題は報告しないでください
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: review_pr.py <diff_file>")
        sys.exit(1)

    diff_path = sys.argv[1]
    with open(diff_path) as f:
        diff_content = f.read()

    if not diff_content.strip():
        print("## AI Review\n\n対象ファイルに変更がありませんでした。")
        return

    pr_title = os.environ.get("PR_TITLE", "")
    pr_body = os.environ.get("PR_BODY", "")

    user_prompt = f"## レビュー対象 PR\n\nPR タイトル: {pr_title}\nPR 説明: {pr_body}\n\n## 変更差分\n\n{diff_content}"

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    review = message.content[0].text
    print(f"## AI Review\n\n{review}")


if __name__ == "__main__":
    main()
