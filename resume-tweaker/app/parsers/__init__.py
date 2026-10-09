"""Format detection and dispatch. Every format is converted to Markdown (SPECIFICATION §5)."""

from dataclasses import dataclass, field
from pathlib import PurePath

from ..errors import ServiceError
from .doc_parser import parse_doc
from .docx_parser import parse_docx
from .markdown_parser import parse_markdown
from .pdf_parser import parse_pdf

EXTENSION_FORMAT = {
    ".pdf": "pdf",
    ".doc": "doc",
    ".docx": "docx",
    ".md": "md",
    ".markdown": "md",
}

# Magic bytes that every genuine file of the format starts with (FR-R4). Markdown is plain text.
MAGIC_BYTES = {
    "pdf": b"%PDF",
    "doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",
    "docx": b"PK\x03\x04",
    "md": None,
}

PARSERS = {
    "pdf": parse_pdf,
    "doc": parse_doc,
    "docx": parse_docx,
    "md": parse_markdown,
}


@dataclass
class ParsedResume:
    markdown: str
    fmt: str
    warnings: list[str] = field(default_factory=list)


def parse_resume(filename: str, data: bytes) -> ParsedResume:
    fmt = EXTENSION_FORMAT.get(PurePath(filename).suffix.lower())
    if fmt is None:
        raise ServiceError(415, "UNSUPPORTED_FORMAT", "Upload a PDF, DOC, DOCX or Markdown file.")

    magic = MAGIC_BYTES[fmt]
    if magic and not data.startswith(magic):
        raise ServiceError(415, "FORMAT_MISMATCH", f"The file content does not look like a .{fmt} file.")

    markdown, warnings = PARSERS[fmt](data)
    return ParsedResume(markdown=markdown, fmt=fmt, warnings=warnings)
