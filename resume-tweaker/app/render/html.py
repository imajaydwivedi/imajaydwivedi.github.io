"""Markdown to standalone HTML. Raw HTML in the source is escaped, so uploaded files cannot inject markup."""

from html import escape
from pathlib import Path

from markdown_it import MarkdownIt

_MARKDOWN = MarkdownIt("commonmark", {"html": False, "breaks": True}).enable("table")
_CSS = (Path(__file__).parent / "resume.css").read_text(encoding="utf-8")
_PREVIEW_CSS = (Path(__file__).parent / "preview.css").read_text(encoding="utf-8")

# Plain-text sentinels survive Markdown rendering untouched and are swapped for <mark> afterwards.
MARK_OPEN = "RTMARKOPEN9Q"
MARK_CLOSE = "RTMARKCLOSE9Q"


def render_body(markdown: str, marked_lines: frozenset[str] = frozenset()) -> str:
    if marked_lines:
        markdown = "\n".join(_mark_line(line) if line in marked_lines else line for line in markdown.split("\n"))
    html = _MARKDOWN.render(markdown)
    return html.replace(MARK_OPEN, "<mark>").replace(MARK_CLOSE, "</mark>")


def _mark_line(line: str) -> str:
    # Keep a list marker in front of the sentinel so the bullet still renders as a list item.
    prefix = "- " if line.startswith("- ") else ""
    return f"{prefix}{MARK_OPEN}{line[len(prefix):]}{MARK_CLOSE}"


def render_document(markdown: str, marked_lines: frozenset[str] = frozenset(), for_pdf: bool = False) -> str:
    title = _title_of(markdown)
    note = ""
    if marked_lines:
        note = '<p class="note">Highlighted text was added from the keywords you kept checked.</p>'
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        f"<style>\n{_CSS}\n</style>\n"
        + ("" if for_pdf else f"<style>\n{_PREVIEW_CSS}\n</style>\n")
        + "</head>\n<body>\n"
        f'<main class="resume">\n{note}\n{render_body(markdown, marked_lines)}</main>\n'
        "</body>\n</html>\n"
    )


def _title_of(markdown: str) -> str:
    for line in markdown.split("\n"):
        if line.startswith("# "):
            return line[2:].strip() or "Resume"
    return "Resume"
