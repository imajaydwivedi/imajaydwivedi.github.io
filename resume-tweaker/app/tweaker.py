"""Tailors a resume's Markdown (SPECIFICATION §4.5). Two operations, neither invents content:

1. Core Competencies: the accepted keywords are listed, four per line, in a section after the
   summary. Only keywords the user confirmed are written, and keywords already in the resume
   are included only when the user keeps them checked.
2. Reordering: bullets inside Skills and Experience sections are sorted so the ones matching
   the job description come first. Wording, dates, and job order are never changed.
"""

import re
from dataclasses import dataclass, field

from .analyzer import contains_term

CORE_NAME = "Core Competencies"
CHUNK_SIZE = 4  # keywords per line, same layout as the LaTeX version
REORDER_HEADING_RE = re.compile(r"^#{1,6}\s+.*\b(skills?|technical skills|experience)\b", re.IGNORECASE)
CORE_HEADING_RE = re.compile(r"^#{1,6}\s+.*\bcore competenc", re.IGNORECASE)
SUMMARY_HEADING_RE = re.compile(r"^#{1,6}\s+.*\b(summary|profile|objective|about me)\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^(#{1,6})\s+")
BULLET_RE = re.compile(r"^- \S")
NAME_RE = re.compile(r"^#\s+(.+?)\s*$")


@dataclass
class TweakResult:
    markdown: str
    added: list[str] = field(default_factory=list)  # keywords now listed in Core Competencies
    marked_lines: frozenset[str] = frozenset()  # exact lines the preview should highlight
    reordered_sections: int = 0


def apply_keywords(markdown: str, terms: list[str], reorder: bool, jd_terms: list[str]) -> TweakResult:
    lines = markdown.split("\n")

    reordered = _reorder_bullets(lines, jd_terms) if reorder else 0

    added = _unique_terms(terms)
    if added:
        existing = _core_section_text(lines)
        added = [term for term in added if not contains_term(term.lower(), existing.lower())]

    marked: frozenset[str] = frozenset()
    if added:
        chunks = [f"- {' | '.join(added[i : i + CHUNK_SIZE])}" for i in range(0, len(added), CHUNK_SIZE)]
        marked = frozenset(chunks)
        core_index = _find_heading(lines, CORE_HEADING_RE)
        if core_index is not None:
            _insert_block(lines, _section_end(lines, core_index), chunks)
        else:
            summary_index = _find_heading(lines, SUMMARY_HEADING_RE)
            insert_at = (
                _section_end(lines, summary_index) if summary_index is not None else _find_first_level2(lines)
            )
            _insert_block(lines, insert_at, [f"## {CORE_NAME}", ""] + chunks)

    if not added and not reordered:
        return TweakResult(markdown=markdown)
    return TweakResult(
        markdown="\n".join(lines),
        added=added,
        marked_lines=marked,
        reordered_sections=reordered,
    )


def extract_name(markdown: str) -> str:
    for line in markdown.split("\n"):
        match = NAME_RE.match(line)
        if match:
            return re.sub(r"[*_`\[\]]", "", match.group(1)).strip() or "Resume"
    return "Resume"


def _unique_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for term in terms:
        key = term.strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(term.strip())
    return result


def _core_section_text(lines: list[str]) -> str:
    index = _find_heading(lines, CORE_HEADING_RE)
    if index is None:
        return ""
    return "\n".join(lines[index : _section_end(lines, index)])


def _reorder_bullets(lines: list[str], jd_terms: list[str]) -> int:
    """Stable-sort each run of top-level bullets inside Skills/Experience sections by JD relevance."""
    if not jd_terms:
        return 0
    changed_runs = 0
    index = 0
    while index < len(lines):
        if not REORDER_HEADING_RE.match(lines[index]):
            index += 1
            continue
        end = _section_end(lines, index)
        position = index + 1
        while position < end:
            if not BULLET_RE.match(lines[position]):
                position += 1
                continue
            run_end = position
            while run_end < end and BULLET_RE.match(lines[run_end]):
                run_end += 1
            run = lines[position:run_end]
            ordered = sorted(run, key=lambda bullet: -_relevance(bullet, jd_terms))  # sort is stable
            if ordered != run:
                lines[position:run_end] = ordered
                changed_runs += 1
            position = run_end
        index = end
    return changed_runs


def _relevance(bullet: str, jd_terms: list[str]) -> int:
    lowered = bullet.lower()
    return sum(1 for term in jd_terms if contains_term(term.lower(), lowered))


def _find_heading(lines: list[str], pattern: re.Pattern) -> int | None:
    for index, line in enumerate(lines):
        if pattern.match(line):
            return index
    return None


def _find_first_level2(lines: list[str]) -> int:
    for index, line in enumerate(lines):
        if line.startswith("## "):
            return index
    return len(lines)


def _section_end(lines: list[str], start: int) -> int:
    """Index of the first line after the section that starts at `start` (or EOF)."""
    level = len(HEADING_RE.match(lines[start]).group(1))
    for index in range(start + 1, len(lines)):
        match = HEADING_RE.match(lines[index])
        if match and len(match.group(1)) <= level:
            return index
    return len(lines)


def _insert_block(lines: list[str], at: int, block: list[str]) -> None:
    # Step back over blank lines so the block sits right after the section's content.
    while at > 0 and not lines[at - 1].strip():
        at -= 1
    # The line at `at` is already blank (or the section ends), so a trailing blank is only needed when it is content.
    trailing = [""] if at < len(lines) and lines[at].strip() else []
    lines[at:at] = [""] + block + trailing
