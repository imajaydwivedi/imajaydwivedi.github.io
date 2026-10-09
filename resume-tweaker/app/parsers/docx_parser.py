import io
import re

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from ..errors import ServiceError

HEADING_STYLE = re.compile(r"^heading (\d)$")


def parse_docx(data: bytes) -> tuple[str, list[str]]:
    try:
        document = Document(io.BytesIO(data))
    except Exception as exc:  # python-docx raises several unrelated exception types on bad input
        raise ServiceError(422, "PARSE_ERROR", "Could not read this Word document.") from exc

    blocks: list[str] = []
    # Walk the body in document order so tables stay between the paragraphs around them.
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            line = _paragraph_to_md(Paragraph(child, document))
            blocks.append(line)
        elif child.tag == qn("w:tbl"):
            # Blank lines around a table so Markdown renders it as a table, not as continued text.
            blocks.extend(["", _table_to_md(Table(child, document)), ""])

    markdown = "\n".join(blocks)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    if not markdown:
        raise ServiceError(422, "PARSE_ERROR", "The Word document has no text.")
    return markdown + "\n", []


def _paragraph_to_md(paragraph: Paragraph) -> str:
    text = _runs_to_md(paragraph)
    if not text:
        return ""

    style = (paragraph.style.name or "").lower() if paragraph.style is not None else ""
    if style == "title":
        return f"# {text}"
    match = HEADING_STYLE.match(style)
    if match:
        level = min(max(int(match.group(1)), 1), 6)
        return f"{'#' * level} {text}"
    if "list" in style:
        return f"- {text}"
    return text


def _runs_to_md(paragraph: Paragraph) -> str:
    # Hyperlink text is not exposed through runs in python-docx; fall back to plain text when they differ.
    run_text = "".join(run.text for run in paragraph.runs)
    if run_text.strip() != paragraph.text.strip():
        return paragraph.text.strip()

    parts = []
    for run in paragraph.runs:
        text = run.text
        core = text.strip()
        if not core:
            parts.append(text)
            continue
        lead = text[: len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()) :]
        if run.bold and run.italic:
            core = f"***{core}***"
        elif run.bold:
            core = f"**{core}**"
        elif run.italic:
            core = f"*{core}*"
        parts.append(f"{lead}{core}{trail}")
    return "".join(parts).strip()


def _table_to_md(table: Table) -> str:
    rows = [
        [cell.text.replace("\n", " ").replace("|", "\\|").strip() for cell in row.cells]
        for row in table.rows
    ]
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(row) + " |" for row in rows[1:]]
    return "\n".join(lines)
