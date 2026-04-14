#!/usr/bin/env python3
"""AI PR review script using Claude API.

Produces structured review output:
- review.md: Structured review with sections
- inline_comments.json: Line-specific comments
- verdict.txt: APPROVED / APPROVED_WITH_WARNINGS / CHANGES_REQUESTED
"""

import json
import os
import re
import sys
from pathlib import Path

import anthropic

DEFAULT_SYSTEM_PROMPT = """\
あなたは ROS 2 と Python に精通したコードレビュアーです。
以下の構造化フォーマットでレビューを出力してください。

## 出力フォーマット（必ずこの順序で出力）

### セクション 1〜6: レビュー本文

```
## Summary
[PR の変更概要と目的を 2-3 文で]

## Code Quality
[命名、構造、重複、可読性の評価]

## Test Coverage
[テストカバレッジの評価。不足しているテストケースの指摘]

## Security
[セキュリティリスクの評価。問題なければ「セキュリティ上の懸念はありません」]

## Recommendations
[改善提案のリスト（番号付き、重要度付き: Critical/Warning/Info）]

## Verdict
[以下のいずれか 1 つだけを記載]
- APPROVED: 問題なし
- APPROVED_WITH_WARNINGS: Warning レベルの指摘あり
- CHANGES_REQUESTED: Critical レベルの指摘あり
```

### セクション 7: インラインコメント

```
## Inline Comments
\u0060\u0060\u0060json
[
  {
    "path": "ファイルパス",
    "line": 行番号,
    "body": "指摘内容（Conventional Comments 形式: issue:/suggestion:/nitpick:）",
    "severity": "high/medium/low"
  }
]
\u0060\u0060\u0060
```

指摘がなければ空配列 `[]` を出力してください。

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

## ノイズ低減指示
- スタイルの好みに基づく指摘は行わないでください
- 既存コードの設計思想の変更提案は行わないでください
- この PR のスコープ外の改善提案は行わないでください
- すでに ruff が検出できる問題は報告しないでください
"""


def load_review_instructions(path: str) -> str:
    """Load review instructions from external file, falling back to default."""
    try:
        return Path(path).read_text()
    except (FileNotFoundError, OSError):
        return DEFAULT_SYSTEM_PROMPT


def extract_verdict(text: str) -> str:
    """Extract verdict string from the API response text."""
    # Look for verdict after "## Verdict" heading
    verdict_match = re.search(r"## Verdict\s*\n(.+?)(?:\n\n|\n##|\Z)", text, re.DOTALL)
    if verdict_match:
        verdict_section = verdict_match.group(1).strip()
        for v in ("CHANGES_REQUESTED", "APPROVED_WITH_WARNINGS", "APPROVED"):
            if v in verdict_section:
                return v

    return "APPROVED_WITH_WARNINGS"


def extract_inline_comments(text: str) -> list:
    """Extract inline comments JSON from the API response text."""
    # Look for JSON code block after "## Inline Comments"
    pattern = r"## Inline Comments\s*\n```json\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return []

    try:
        comments = json.loads(match.group(1).strip())
        if not isinstance(comments, list):
            return []
        return comments[:10]  # Cap at 10
    except (json.JSONDecodeError, ValueError):
        return []


def extract_review_body(text: str) -> str:
    """Extract the review body (everything before Inline Comments section)."""
    # Remove the Inline Comments section
    parts = re.split(r"\n## Inline Comments\b", text, maxsplit=1)
    return parts[0].strip()


def run_review(diff_path: str) -> None:
    """Run the AI review and produce output files."""
    with open(diff_path) as f:
        diff_content = f.read()

    if not diff_content.strip():
        Path("review.md").write_text("## AI Review\n\n対象ファイルに変更がありませんでした。\n")
        Path("inline_comments.json").write_text("[]")
        Path("verdict.txt").write_text("APPROVED")
        return

    pr_title = os.environ.get("PR_TITLE", "")
    pr_body = os.environ.get("PR_BODY", "")

    # Load review instructions
    script_dir = Path(__file__).resolve().parent
    instructions_path = script_dir / "review-instructions.md"
    system_prompt = load_review_instructions(str(instructions_path))

    user_prompt = f"## レビュー対象 PR\n\nPR タイトル: {pr_title}\nPR 説明: {pr_body}\n\n## 変更差分\n\n{diff_content}"

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=os.environ.get("AI_REVIEW_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    response_text = message.content[0].text

    # Extract and write outputs
    review_body = extract_review_body(response_text)
    Path("review.md").write_text(f"## AI Review\n\n{review_body}\n")

    inline_comments = extract_inline_comments(response_text)
    Path("inline_comments.json").write_text(json.dumps(inline_comments, indent=2))

    verdict = extract_verdict(response_text)
    Path("verdict.txt").write_text(verdict)


def main():
    if len(sys.argv) < 2:
        print("Usage: review_pr.py <diff_file>", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "::error::ANTHROPIC_API_KEY is not set. Please add it to GitHub Secrets (Settings → Secrets → Actions).",
            file=sys.stderr,
        )
        sys.exit(1)

    run_review(sys.argv[1])


if __name__ == "__main__":
    main()
