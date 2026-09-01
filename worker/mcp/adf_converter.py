"""Vendored Markdown → Atlassian Document Format (ADF) converter.

Source of truth when present on this machine:
`/Users/nick.sanchez/mcp-servers/atlassian_mcp/shared/adf_converter.py`

Supports headings, bold, links, bullet lists, task lists, and tables for Jira comments.
Runtime import prefers the external path via `worker.mcp.adf`.
"""
import re
import uuid
from typing import Any, Dict, List


def _text_node(text: str) -> Dict[str, Any]:
    return {"type": "text", "text": text}


def _parse_inline(text: str) -> List[Dict[str, Any]]:
    """Parse inline markdown for bold, italic, code, and links into ADF text nodes."""
    if not text:
        return []

    # Pattern for [text](url), **bold**, *italic*, and `code`
    # Order matters: **bold** must come before *italic*
    pattern = re.compile(r"(\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|\*([^*]+)\*|`([^`]+)`)")
    nodes: List[Dict[str, Any]] = []
    pos = 0

    while pos < len(text):
        match = pattern.search(text, pos)
        if not match:
            if pos < len(text):
                nodes.append(_text_node(text[pos:]))
            break

        if match.start() > pos:
            nodes.append(_text_node(text[pos:match.start()]))

        # Link: [text](url)
        if match.group(2) and match.group(3):
            nodes.append({
                "type": "text",
                "text": match.group(2),
                "marks": [{
                    "type": "link",
                    "attrs": {"href": match.group(3)}
                }]
            })

        # Bold: **text**
        elif match.group(4):
            inner_text = match.group(4)
            # Detect nested code: **`code`**
            if inner_text.startswith("`") and inner_text.endswith("`"):
                nodes.append({
                    "type": "text",
                    "text": inner_text[1:-1],
                    "marks": [{"type": "code"}]
                })
            else:
                nodes.append({
                    "type": "text",
                    "text": inner_text,
                    "marks": [{"type": "strong"}]
                })

        # Italic: *text*
        elif match.group(5):
            nodes.append({
                "type": "text",
                "text": match.group(5),
                "marks": [{"type": "em"}]
            })

        # Code: `text`
        elif match.group(6):
            nodes.append({
                "type": "text",
                "text": match.group(6),
                "marks": [{"type": "code"}]
            })

        pos = match.end()

    return nodes


def _heading(level: int, text: str) -> Dict[str, Any]:
    return {"type": "heading", "attrs": {"level": level}, "content": _parse_inline(text)}


def _paragraph(text: str) -> Dict[str, Any]:
    return {"type": "paragraph", "content": _parse_inline(text)}


def _bullet_list(items: List[str]) -> Dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [
                    {"type": "paragraph", "content": _parse_inline(item.strip())}
                ],
            }
            for item in items
        ],
    }


def _task_list(items: List[tuple]) -> Dict[str, Any]:
    """Build an ADF task list from (checked, text) tuples."""
    return {
        "type": "taskList",
        "attrs": {"localId": str(uuid.uuid4())[:8]},
        "content": [
            {
                "type": "taskItem",
                "attrs": {
                    "localId": str(uuid.uuid4())[:8],
                    "state": "DONE" if checked else "TODO"
                },
                "content": _parse_inline(text.strip())
            }
            for checked, text in items
        ],
    }


def _is_task_item(line: str) -> tuple:
    """Check if line is a task item. Returns (is_task, is_checked, text) or (False, False, '')."""
    stripped = line.strip()
    # Match: - [ ] text or - [x] text or - [X] text
    match = re.match(r'^[-*]\s+\[([ xX])\]\s+(.*)$', stripped)
    if match:
        checked = match.group(1).lower() == 'x'
        text = match.group(2)
        return (True, checked, text)
    return (False, False, '')


def _parse_table_row(line: str) -> List[str]:
    """Parse a markdown table row into cell values."""
    # Remove leading/trailing pipes and split
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip() for cell in line.split("|")]


def _is_table_separator(line: str) -> bool:
    """Check if line is a table separator (|---|---|)."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    # Remove pipes and check if only dashes, colons, and spaces remain
    content = stripped.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")
    return len(content) == 0 and "-" in stripped


def _table(header_cells: List[str], data_rows: List[List[str]]) -> Dict[str, Any]:
    """Build an ADF table from header and data rows."""
    rows = []

    # Header row
    header_row = {
        "type": "tableRow",
        "content": [
            {
                "type": "tableHeader",
                "attrs": {},
                "content": [{"type": "paragraph", "content": _parse_inline(cell)}]
            }
            for cell in header_cells
        ]
    }
    rows.append(header_row)

    # Data rows
    for data_cells in data_rows:
        # Pad cells if row has fewer columns than header
        while len(data_cells) < len(header_cells):
            data_cells.append("")

        data_row = {
            "type": "tableRow",
            "content": [
                {
                    "type": "tableCell",
                    "attrs": {},
                    "content": [{"type": "paragraph", "content": _parse_inline(cell)}]
                }
                for cell in data_cells[:len(header_cells)]  # Trim extra columns
            ]
        }
        rows.append(data_row)

    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": rows
    }


def convert_markdown_to_adf(markdown_text: str) -> Dict[str, Any]:
    """Convert a limited markdown subset to Jira ADF doc structure."""
    lines = markdown_text.splitlines()
    content: List[Dict[str, Any]] = []
    i = 0

    while i < len(lines):
        line = lines[i].rstrip("\n")
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Horizontal Rule
        if stripped == "---":
            content.append({"type": "rule"})
            i += 1
            continue

        # Code block detection (starts with ```)
        if stripped.startswith("```"):
            language = stripped[3:].strip()
            i += 1
            code_lines = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1

            if i < len(lines):  # Skip closing ```
                i += 1

            # Normalize: collapse multiple consecutive blank lines into one
            code_text = "\n".join(code_lines)
            code_text = re.sub(r'\n{3,}', '\n\n', code_text)  # 3+ newlines -> 2
            code_text = re.sub(r'^\n+', '', code_text)  # Strip leading blank lines
            code_text = re.sub(r'\n+$', '', code_text)  # Strip trailing blank lines
            node = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": code_text}]
            }
            if language:
                node["attrs"] = {"language": language}
            content.append(node)
            continue

        if stripped.startswith("#### "):
            content.append(_heading(4, stripped[5:]))
            i += 1
            continue

        if stripped.startswith("### "):
            content.append(_heading(3, stripped[4:]))
            i += 1
            continue

        if stripped.startswith("## "):
            content.append(_heading(2, stripped[3:]))
            i += 1
            continue

        # Table detection (line starts with |)
        if stripped.startswith("|") and "|" in stripped[1:]:
            # Collect all table lines
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1

            if len(table_lines) >= 2:
                # First line is header
                header_cells = _parse_table_row(table_lines[0])

                # Find and skip separator line, collect data rows
                data_rows = []
                for tl in table_lines[1:]:
                    if _is_table_separator(tl):
                        continue
                    data_rows.append(_parse_table_row(tl))

                if header_cells:
                    content.append(_table(header_cells, data_rows))
                    continue

        # Task list detection (checkboxes: - [ ] or - [x])
        is_task, is_checked, task_text = _is_task_item(stripped)
        if is_task:
            task_items: List[tuple] = []
            while i < len(lines):
                is_t, is_c, t_text = _is_task_item(lines[i].strip())
                if not is_t:
                    break
                task_items.append((is_c, t_text))
                i += 1
            content.append(_task_list(task_items))
            continue

        # Bullet list detection
        if stripped.startswith(("- ", "* ")):
            bullet_items: List[str] = []
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                bullet_items.append(lines[i].strip()[2:])
                i += 1
            content.append(_bullet_list(bullet_items))
            continue

        # Paragraph
        nodes = _parse_inline(line.strip())
        if nodes:
            content.append({"type": "paragraph", "content": nodes})
        i += 1

    if not content:
        content.append({"type": "paragraph", "content": []})

    return {"type": "doc", "version": 1, "content": content}

def convert_adf_to_markdown(adf_content: dict) -> str:
    """Convert Atlassian Document Format (ADF) to Markdown."""
    if not adf_content:
        return ""

    lines = []

    def process_node(node):
        node_type = node.get("type")
        if node_type == "paragraph":
            content = "".join(get_inline_content(node))
            if content:
                lines.append(content)
                lines.append("")
        elif node_type == "heading":
            level = node.get("attrs", {}).get("level", 1)
            content = "".join(get_inline_content(node))
            lines.append(f"{'#' * level} {content}")
            lines.append("")
        elif node_type == "bulletList":
            for item in node.get("content", []):
                content = "".join(get_inline_content(item))
                lines.append(f"- {content}")
            lines.append("")
        elif node_type == "orderedList":
            for i, item in enumerate(node.get("content", []), 1):
                content = "".join(get_inline_content(item))
                lines.append(f"{i}. {content}")
            lines.append("")
        elif node_type == "codeBlock":
            content = "".join(get_inline_content(node))
            language = node.get("attrs", {}).get("language", "")
            lines.append(f"```{language}")
            lines.append(content)
            lines.append("```")
            lines.append("")
        elif "content" in node:
            for child in node.get("content", []):
                process_node(child)

    def get_inline_content(node) -> list:
        parts = []
        for child in node.get("content", []):
            child_type = child.get("type")
            if child_type == "text":
                text = child.get("text", "")
                for mark in child.get("marks", []):
                    mark_type = mark.get("type")
                    if mark_type == "strong":
                        text = f"**{text}**"
                    elif mark_type == "em":
                        text = f"_{text}_"
                    elif mark_type == "code":
                        text = f"`{text}`"
                    elif mark_type == "link":
                        href = mark.get("attrs", {}).get("href", "")
                        text = f"[{text}]({href})"
                parts.append(text)
            elif child_type == "hardBreak":
                parts.append("\n")
            elif "content" in child:
                parts.extend(get_inline_content(child))
        return parts

    process_node(adf_content)
    return "\n".join(lines).strip()
