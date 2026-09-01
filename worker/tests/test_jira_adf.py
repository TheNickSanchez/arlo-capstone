"""ADF helpers for the live Jira Cloud client (no network)."""

from __future__ import annotations

from worker.mcp.jira_cloud import adf_to_text, text_to_adf


def test_adf_round_trip_plain_paragraphs() -> None:
    body = "Line one\n\nLine two"
    adf = text_to_adf(body)
    assert adf["type"] == "doc"
    assert adf_to_text(adf) == "Line one\nLine two"


def test_adf_to_text_nested_paragraphs() -> None:
    node = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "Hello"}],
            },
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": "World"}],
            },
        ],
    }
    assert adf_to_text(node) == "Hello\nWorld"
