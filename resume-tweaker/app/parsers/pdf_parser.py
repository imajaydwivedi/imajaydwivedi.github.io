"""Best-effort PDF to Markdown. Layout is inferred from word positions and font sizes."""

import io
import re
from collections import Counter
from statistics import median

import pdfplumber

from ..errors import ServiceError

BULLET_RE = re.compile(r"^[•·▪●◦\-–*]\s+")
LINE_TOLERANCE = 2.0  # points; words whose tops differ by less belong to the same line


def parse_pdf(data: bytes) -> tuple[str, list[str]]:
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as exc:
        raise ServiceError(422, "PARSE_ERROR", "Could not read this PDF.") from exc

    lines: list[dict] = []
    with pdf:
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["size", "fontname"], keep_blank_chars=False)
            lines.extend(_group_lines(words))

    if not lines:
        raise ServiceError(422, "PARSE_ERROR", "No text found. Scanned (image-only) PDFs are not supported.")

    base = _base_font_size(lines)
    blocks = [_line_to_md(line, base) for line in lines]
    markdown = _join_blocks(blocks)
    warnings = ["PDF layout was inferred from text positions. Check headings and bullets in the preview."]
    return markdown + "\n", warnings


def _group_lines(words: list[dict]) -> list[dict]:
    grouped: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if grouped and abs(word["top"] - grouped[-1][0]["top"]) <= LINE_TOLERANCE:
            grouped[-1].append(word)
        else:
            grouped.append([word])

    result = []
    for group in grouped:
        group.sort(key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in group).strip()
        if not text:
            continue
        result.append(
            {
                "text": text,
                "size": median(w["size"] for w in group),
                "bold": all("bold" in w["fontname"].lower() for w in group),
            }
        )
    return result


def _base_font_size(lines: list[dict]) -> float:
    # The most common size, weighted by how much text uses it, is treated as body text.
    weights = Counter()
    for line in lines:
        weights[round(line["size"], 1)] += len(line["text"])
    return weights.most_common(1)[0][0]


def _line_to_md(line: dict, base: float) -> tuple[str, str]:
    text, size = line["text"], line["size"]
    if BULLET_RE.match(text):
        return "bullet", "- " + BULLET_RE.sub("", text)
    if size >= base * 1.5 and len(text) < 80:
        return "heading", f"# {text}"
    if (size >= base * 1.15 or line["bold"]) and len(text) < 60:
        return "heading", f"## {text}"
    return "text", text + "  "  # two trailing spaces = hard line break


def _join_blocks(blocks: list[tuple[str, str]]) -> str:
    out = []
    previous = None
    for kind, content in blocks:
        if out:
            out.append("\n" if previous == kind == "bullet" else "\n\n")
        out.append(content)
        previous = kind
    return "".join(out).strip()
