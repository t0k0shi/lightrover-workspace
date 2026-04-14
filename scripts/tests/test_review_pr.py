"""Tests for review_pr.py structured output."""

import json
from unittest.mock import MagicMock, patch

# ── Helper: build a mock Claude API response ──


def _mock_response(text: str) -> MagicMock:
    """Create a mock Anthropic message response."""
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


# ── Tests for output file generation ──


class TestReviewOutputFiles:
    """review_pr.py should produce review.md, inline_comments.json, verdict.txt."""

    def test_produces_three_output_files(self, tmp_path, monkeypatch):
        """Running review_pr.py creates the three expected output files."""
        from scripts.review_pr import run_review

        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("diff --git a/foo.py b/foo.py\n+print('hello')")

        monkeypatch.setenv("PR_TITLE", "test PR")
        monkeypatch.setenv("PR_BODY", "test body")

        api_response = (
            "## Summary\nTest summary\n\n"
            "## Code Quality\nGood\n\n"
            "## Test Coverage\nAdequate\n\n"
            "## Security\nNo issues\n\n"
            "## Recommendations\n1. None\n\n"
            "## Verdict\nAPPROVED\n\n"
            "## Inline Comments\n"
            "```json\n"
            '[{"path": "foo.py", "line": 1, "body": "looks good", "severity": "low"}]\n'
            "```"
        )

        with patch("scripts.review_pr.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(api_response)

            monkeypatch.chdir(tmp_path)
            run_review(str(diff_file))

        assert (tmp_path / "review.md").exists()
        assert (tmp_path / "inline_comments.json").exists()
        assert (tmp_path / "verdict.txt").exists()

    def test_review_md_contains_structured_sections(self, tmp_path, monkeypatch):
        """review.md should contain the required sections."""
        from scripts.review_pr import run_review

        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("diff --git a/foo.py b/foo.py\n+x = 1")

        monkeypatch.setenv("PR_TITLE", "test")
        monkeypatch.setenv("PR_BODY", "")

        api_response = (
            "## Summary\nChanged x\n\n"
            "## Code Quality\nFine\n\n"
            "## Test Coverage\nNo tests\n\n"
            "## Security\nOK\n\n"
            "## Recommendations\n1. Add tests\n\n"
            "## Verdict\nAPPROVED_WITH_WARNINGS\n\n"
            "## Inline Comments\n```json\n[]\n```"
        )

        with patch("scripts.review_pr.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(api_response)

            monkeypatch.chdir(tmp_path)
            run_review(str(diff_file))

        review = (tmp_path / "review.md").read_text()
        for section in ["Summary", "Code Quality", "Test Coverage", "Security", "Recommendations"]:
            assert f"## {section}" in review

    def test_verdict_file_contains_valid_verdict(self, tmp_path, monkeypatch):
        """verdict.txt should contain one of the three valid verdicts."""
        from scripts.review_pr import run_review

        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("diff --git a/foo.py b/foo.py\n+x = 1")

        monkeypatch.setenv("PR_TITLE", "test")
        monkeypatch.setenv("PR_BODY", "")

        api_response = (
            "## Summary\nTest\n\n"
            "## Code Quality\nOK\n\n"
            "## Test Coverage\nOK\n\n"
            "## Security\nOK\n\n"
            "## Recommendations\nNone\n\n"
            "## Verdict\nCHANGES_REQUESTED\n\n"
            "## Inline Comments\n```json\n[]\n```"
        )

        with patch("scripts.review_pr.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(api_response)

            monkeypatch.chdir(tmp_path)
            run_review(str(diff_file))

        verdict = (tmp_path / "verdict.txt").read_text().strip()
        assert verdict in ("APPROVED", "APPROVED_WITH_WARNINGS", "CHANGES_REQUESTED")

    def test_inline_comments_json_is_valid(self, tmp_path, monkeypatch):
        """inline_comments.json should be valid JSON with correct schema."""
        from scripts.review_pr import run_review

        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("diff --git a/foo.py b/foo.py\n+x = 1")

        monkeypatch.setenv("PR_TITLE", "test")
        monkeypatch.setenv("PR_BODY", "")

        api_response = (
            "## Summary\nTest\n\n"
            "## Code Quality\nOK\n\n"
            "## Test Coverage\nOK\n\n"
            "## Security\nOK\n\n"
            "## Recommendations\nNone\n\n"
            "## Verdict\nAPPROVED\n\n"
            "## Inline Comments\n```json\n"
            '[{"path": "foo.py", "line": 10, "body": "issue: potential bug", "severity": "high"}]\n'
            "```"
        )

        with patch("scripts.review_pr.anthropic") as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.Anthropic.return_value = mock_client
            mock_client.messages.create.return_value = _mock_response(api_response)

            monkeypatch.chdir(tmp_path)
            run_review(str(diff_file))

        comments = json.loads((tmp_path / "inline_comments.json").read_text())
        assert isinstance(comments, list)
        assert len(comments) == 1
        assert comments[0]["path"] == "foo.py"
        assert comments[0]["line"] == 10
        assert "body" in comments[0]
        assert "severity" in comments[0]

    def test_empty_diff_produces_approved(self, tmp_path, monkeypatch):
        """An empty diff should produce APPROVED verdict without calling the API."""
        from scripts.review_pr import run_review

        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("")

        monkeypatch.chdir(tmp_path)
        run_review(str(diff_file))

        verdict = (tmp_path / "verdict.txt").read_text().strip()
        assert verdict == "APPROVED"

        review = (tmp_path / "review.md").read_text()
        assert "対象ファイルに変更がありませんでした" in review

    def test_uses_review_instructions_file(self, tmp_path, monkeypatch):
        """review_pr.py should load review-instructions.md if it exists."""
        from scripts.review_pr import load_review_instructions

        instructions_file = tmp_path / "review-instructions.md"
        instructions_file.write_text("Custom review rules here")

        result = load_review_instructions(str(instructions_file))
        assert "Custom review rules here" in result

    def test_missing_instructions_uses_default(self, tmp_path):
        """Missing review-instructions.md should fall back to built-in prompt."""
        from scripts.review_pr import load_review_instructions

        result = load_review_instructions(str(tmp_path / "nonexistent.md"))
        assert result is not None
        assert len(result) > 0


class TestVerdictExtraction:
    """Tests for extracting verdict from API response."""

    def test_extracts_approved(self):
        from scripts.review_pr import extract_verdict

        text = "## Verdict\nAPPROVED\n\nThe code looks good."
        assert extract_verdict(text) == "APPROVED"

    def test_extracts_changes_requested(self):
        from scripts.review_pr import extract_verdict

        text = "## Verdict\nCHANGES_REQUESTED\n\nSecurity issues found."
        assert extract_verdict(text) == "CHANGES_REQUESTED"

    def test_extracts_approved_with_warnings(self):
        from scripts.review_pr import extract_verdict

        text = "## Verdict\nAPPROVED_WITH_WARNINGS\n\nMinor issues."
        assert extract_verdict(text) == "APPROVED_WITH_WARNINGS"

    def test_defaults_to_approved_with_warnings_if_unclear(self):
        from scripts.review_pr import extract_verdict

        text = "## Verdict\nSomething unexpected\n\n"
        assert extract_verdict(text) == "APPROVED_WITH_WARNINGS"


class TestInlineCommentsExtraction:
    """Tests for extracting inline comments JSON from API response."""

    def test_extracts_json_from_code_block(self):
        from scripts.review_pr import extract_inline_comments

        text = '## Inline Comments\n```json\n[{"path": "a.py", "line": 1, "body": "fix", "severity": "high"}]\n```'
        result = extract_inline_comments(text)
        assert len(result) == 1
        assert result[0]["path"] == "a.py"

    def test_returns_empty_list_on_no_comments(self):
        from scripts.review_pr import extract_inline_comments

        text = "## Inline Comments\n```json\n[]\n```"
        result = extract_inline_comments(text)
        assert result == []

    def test_returns_empty_list_on_missing_section(self):
        from scripts.review_pr import extract_inline_comments

        text = "## Summary\nNo inline comments section here."
        result = extract_inline_comments(text)
        assert result == []

    def test_caps_at_10_comments(self):
        from scripts.review_pr import extract_inline_comments

        comments = [{"path": f"f{i}.py", "line": i, "body": f"issue {i}", "severity": "low"} for i in range(15)]
        text = f"## Inline Comments\n```json\n{json.dumps(comments)}\n```"
        result = extract_inline_comments(text)
        assert len(result) == 10
