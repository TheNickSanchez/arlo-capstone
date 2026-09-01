"""Jira Cloud REST (v3) used by the Jira MCP server when Atlassian creds are set.

Same authorized actions as the fixture stub (`jira_get_ticket`, `jira_post_comment`).
No other Jira verbs are implemented in this slice (no transition/close).
"""

from __future__ import annotations

from typing import Any

import httpx

from backend.app.config import settings


def live_jira_configured() -> bool:
    return settings.live_jira_configured()


def _base_url() -> str:
    site = settings.live_jira_site()
    if site.startswith("http"):
        return site.rstrip("/")
    return f"https://{site}.atlassian.net"


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=_base_url(),
        auth=(settings.live_jira_email(), settings.live_jira_api_token()),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30.0,
    )


def adf_to_text(node: Any) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(part for part in (adf_to_text(item) for item in node) if part)
    if isinstance(node, dict):
        if node.get("type") == "text":
            return str(node.get("text") or "")
        inner = adf_to_text(node.get("content") or [])
        if node.get("type") in {"paragraph", "heading", "blockquote", "listItem"}:
            return inner
        return inner
    return ""


def text_to_adf(body: str) -> dict[str, Any]:
    lines = body.replace("\r\n", "\n").split("\n")
    paragraphs: list[dict[str, Any]] = []
    for line in lines:
        if line == "":
            paragraphs.append({"type": "paragraph", "content": []})
            continue
        paragraphs.append(
            {"type": "paragraph", "content": [{"type": "text", "text": line}]}
        )
    if not paragraphs:
        paragraphs = [{"type": "paragraph", "content": []}]
    return {"type": "doc", "version": 1, "content": paragraphs}


def get_ticket(ticket_key: str) -> dict[str, Any]:
    with _client() as client:
        response = client.get(
            f"/rest/api/3/issue/{ticket_key}",
            params={
                "fields": "summary,description,status,assignee,comment,issuetype,priority,labels,reporter"
            },
        )
        if response.status_code == 404:
            return {"found": False, "ticket_key": ticket_key}
        response.raise_for_status()
        issue = response.json()

    fields = issue.get("fields") or {}
    assignee = fields.get("assignee") or {}
    comments_field = fields.get("comment") or {}
    comments = []
    for comment in comments_field.get("comments") or []:
        comments.append(
            {
                "body": adf_to_text(comment.get("body")),
                "at": comment.get("created"),
                "author": (comment.get("author") or {}).get("displayName"),
            }
        )
    return {
        "found": True,
        "ticket_key": issue.get("key") or ticket_key,
        "summary": fields.get("summary") or "",
        "description": adf_to_text(fields.get("description")),
        "status": (fields.get("status") or {}).get("name") or "",
        "assignee": assignee.get("displayName") or assignee.get("emailAddress") or "",
        "issue_type": (fields.get("issuetype") or {}).get("name") or "",
        "priority": (fields.get("priority") or {}).get("name") or "",
        "labels": fields.get("labels") or [],
        "comments": comments,
        "url": f"{_base_url()}/browse/{issue.get('key') or ticket_key}",
    }


def post_comment(ticket_key: str, body: str) -> dict[str, Any]:
    with _client() as client:
        response = client.post(
            f"/rest/api/3/issue/{ticket_key}/comment",
            json={"body": text_to_adf(body)},
        )
        response.raise_for_status()
        payload = response.json()
    return {
        "ok": True,
        "ticket_key": ticket_key,
        "comment_id": payload.get("id"),
        "url": f"{_base_url()}/browse/{ticket_key}",
    }
