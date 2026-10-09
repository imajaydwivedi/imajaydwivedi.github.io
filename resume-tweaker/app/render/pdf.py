from weasyprint import HTML

from .html import render_document


def render_pdf(markdown: str) -> bytes:
    return HTML(string=render_document(markdown, for_pdf=True)).write_pdf()
