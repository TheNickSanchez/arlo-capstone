"""ADF helpers for the live Jira Cloud client (no network)."""

from __future__ import annotations

from worker.mcp.adf import convert_markdown_to_adf
from worker.mcp.jira_cloud import adf_to_text, comment_body_to_adf, text_to_adf


def test_adf_round_trip_plain_paragraphs() -> None:
    body = "Line one\n\nLine two"
    adf = text_to_adf(body)
    assert adf["type"] == "doc"
    assert adf_to_text(adf) == "Line one\nLine two"


def test_markdown_comment_uses_native_adf_marks() -> None:
    markdown = (
        "[Arlo] Investigation Summary\n\n"
        "**Business Impact & Risk**\n"
        "Twelve endpoints are exposed.\n\n"
        "**Recommended Action Plan**\n"
        "* Patch the runtime\n"
        "* Confirm inventory\n"
    )
    adf = comment_body_to_adf(markdown)
    assert adf["type"] == "doc"
    assert convert_markdown_to_adf(markdown)["type"] == "doc"
    types = [node.get("type") for node in adf["content"]]
    assert "bulletList" in types
    marks = [
        mark.get("type")
        for node in adf["content"]
        if node.get("type") == "paragraph"
        for child in node.get("content") or []
        for mark in child.get("marks") or []
    ]
    assert "strong" in marks


def test_existing_adf_doc_is_passed_through() -> None:
    doc = {"type": "doc", "version": 1, "content": []}
    assert comment_body_to_adf(doc) is doc


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
