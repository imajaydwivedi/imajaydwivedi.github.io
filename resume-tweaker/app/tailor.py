"""Rule-based LaTeX resume tailoring. No LLM, no fabrication.

Logic follows Manisha's tailor (help-from-manisha.txt):
  - Find catalog keywords that appear in the job description.
  - Split them into "covered" (already in the resume text) and "gaps" (not in it).
  - Reorder existing Skills / Experience bullets so JD-relevant, already-true
    content comes first. Wording and job order are never changed.
  - Add a Core Competencies section built only from covered keywords, plus any
    gap keywords the user explicitly confirmed.

Differences from the original script:
  - "%" preceded by a backslash (an escaped percent sign) is no longer treated as a comment.
  - Short ambiguous acronyms (HA, DR, ML) are case-sensitive, like Go and R, so prose
    such as "ha" or "dr." does not produce false matches.
  - If the resume already has a Core Competencies section, no second one is added.
  - "Professional Summary" is accepted as the summary heading.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache

from .keywords import KEYWORD_GROUPS

ALIAS_BY_LABEL = dict(KEYWORD_GROUPS)

# Aliases that double as ordinary words or are very short. Matched case-sensitively.
CASE_SENSITIVE_ALIASES = {
    "Go", "R", "HA", "DR", "ML", "SAN", "NAS",
    # Short acronyms and words that are also common prose ("react", "excel at")
    "MQ", "SOX", "GPU", "HPC", "TCP", "UDP", "NFR", "React", "Excel",
    "XDP", "NTP", "PTP", "MCP", "RTO", "RPO", "Lambda",
    "VLDB", "VLDBs", "DBCC", "NVMe", "EBS", "SSMS",
    "QA", "E2E", "PII",
}

REORDER_SECTION_NAMES = {"skills", "technical skills", "experience"}
SUMMARY_SECTION_NAMES = {"summary", "profile", "professional summary"}
CORE_SECTION_NAME = "core competencies"
EXPERIENCE_SECTION_NAMES = {"experience"}

LATEX_SPECIAL = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


@dataclass
class TailorResult:
    tex: str
    matched: list[str]
    gaps: list[str]
    core_keywords: list[str]
    reordered_sections: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def latex_escape(text: str) -> str:
    return "".join(LATEX_SPECIAL.get(c, c) for c in text)


def strip_latex(text: str) -> str:
    """Crude LaTeX to plain text. Good enough for keyword searching."""
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\(textbf|textit|emph)\{([^}]*)\}", r" \2 ", text)
    text = re.sub(r"\\[a-zA-Z]+\{[^}]*\}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = re.sub(r"[{}]", " ", text)
    return text


@lru_cache(maxsize=None)
def _alias_pattern(alias: str) -> re.Pattern:
    flags = 0 if alias in CASE_SENSITIVE_ALIASES else re.IGNORECASE
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(alias) + r"(?![A-Za-z0-9])", flags)


def _group_in_text(text: str, aliases) -> bool:
    return any(_alias_pattern(alias).search(text) for alias in aliases)


def extract_jd_keywords(jd_text: str) -> list[str]:
    return [label for label, aliases in KEYWORD_GROUPS if _group_in_text(jd_text, aliases)]


def analyze(resume_tex: str, jd_text: str) -> tuple[list[str], list[str]]:
    """Return (covered, gaps). Covered keywords appear in the resume; gaps do not."""
    resume_plain = strip_latex(resume_tex)
    jd_keywords = extract_jd_keywords(jd_text)
    covered = [k for k in jd_keywords if _group_in_text(resume_plain, ALIAS_BY_LABEL[k])]
    gaps = [k for k in jd_keywords if k not in covered]
    return covered, gaps


def match_score(
    resume_tex: str,
    jd_text: str,
    include_keywords: list[str] | None = None,
    additions: list[dict] | None = None,
) -> dict:
    """Percent of job keywords the resume covers, counting the user's choices so far.

    A keyword in the resume counts in full. A missing keyword counts in full when the user
    wrote an experience bullet for it, and half when only ticked (Core Competencies only).
    Unticked keywords count for nothing. Bullets that do not contain their keyword are ignored.
    """
    covered, gaps = analyze(resume_tex, jd_text)
    total = len(covered) + len(gaps)
    if not total:
        return {"percent": None, "covered": 0, "total": 0}
    ticked = {k for k in include_keywords or [] if k in gaps}
    with_bullet = {
        a["keyword"] for a in additions or []
        if a["keyword"] in gaps and _group_in_text(" ".join(a["bullet"].split()), ALIAS_BY_LABEL[a["keyword"]])
    }
    points = len(covered) + sum(
        1.0 if k in with_bullet else 0.5 if k in ticked else 0.0 for k in gaps
    )
    return {"percent": round(100 * points / total), "covered": len(covered), "total": total}


def _count_matches(fragment: str, keywords: list[str]) -> int:
    plain = strip_latex(fragment)
    return sum(1 for k in keywords if _group_in_text(plain, ALIAS_BY_LABEL.get(k, [k])))


def _split_items(inner: str) -> list[str]:
    parts = re.split(r"(?=\\item)", inner)
    return [p for p in parts if p.strip().startswith("\\item")]


def _reorder_itemize_inner(inner: str, keywords: list[str]) -> str:
    items = _split_items(inner)
    if len(items) < 2:
        return inner
    # Stable sort: most keyword hits first, original order kept for ties.
    scored = sorted(
        ((-_count_matches(item, keywords), idx, item) for idx, item in enumerate(items)),
        key=lambda x: (x[0], x[1]),
    )
    return "\n" + "\n".join("  " + item.strip() for _, _, item in scored) + "\n"


def _reorder_itemize_blocks(text: str, keywords: list[str]) -> str:
    def repl(m: re.Match) -> str:
        return "\\begin{itemize}" + _reorder_itemize_inner(m.group(1), keywords) + "\\end{itemize}"

    return re.sub(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", repl, text, flags=re.DOTALL)


def _core_item_lines(keywords: list[str], chunk_size: int = 4) -> list[str]:
    escaped = [latex_escape(k) for k in keywords]
    chunks = [escaped[i : i + chunk_size] for i in range(0, len(escaped), chunk_size)]
    return ["    \\item " + " \\quad\\textbar\\quad ".join(chunk) for chunk in chunks]


def build_core_competencies(keywords: list[str], chunk_size: int = 4) -> str:
    lines = _core_item_lines(keywords, chunk_size)
    return (
        "\n% --- Core Competencies (auto-generated: JD keywords already in your resume,"
        " plus any gap keywords you confirmed) ---\n"
        "\\section{Core Competencies}\n\n"
        "\\begin{itemize}\n" + "\n".join(lines) + "\n\\end{itemize}\n"
    )


def _core_label(item: str) -> str:
    """Bold label of a Core Competencies line, e.g. 'Cloud & Containers'. Falls back to the text."""
    m = re.search(r"\\textbf\{([^}]*)\}", item)
    if m:
        return m.group(1).replace("\\&", "&").strip().rstrip(":").strip()
    return " ".join(strip_latex(item).split())[:40] or "Untitled"


def core_subsections(resume_tex: str) -> list[dict]:
    """Lines of the existing Core Competencies list, in order, for the placement picker."""
    _, segments = _section_segments(resume_tex)
    for seg in segments:
        if seg["name"] != CORE_SECTION_NAME:
            continue
        m = ITEMIZE_RE.search(seg["text"])
        if not m:
            return []
        items = [p for p in re.split(r"(?=\\item)", m.group(1)) if p.strip().startswith("\\item")]
        return [{"index": i, "label": _core_label(item)} for i, item in enumerate(items)]
    return []


def place_in_core(section_text: str, existing: dict[int, list[str]], new: dict[str, list[str]]) -> str:
    """Put keywords into chosen Core Competencies lines.

    existing: line index -> keywords to append to that line's list.
    new: label -> keywords for a new bold-labelled line added at the end.
    """
    m = ITEMIZE_RE.search(section_text)
    if not m:
        return section_text
    pieces = re.split(r"(?=\\item)", m.group(1))
    lead, items = pieces[0], pieces[1:]
    for idx, keywords in existing.items():
        body = items[idx].rstrip()
        trailing = items[idx][len(body):]
        items[idx] = body + ", " + ", ".join(latex_escape(k) for k in keywords) + trailing
    for label, keywords in new.items():
        if items and not items[-1].endswith("\n"):
            items[-1] += "\n"
        text = ", ".join(latex_escape(k) for k in keywords)
        items.append(f"  \\item \\textbf{{{latex_escape(label)}:}} {text}\n")
    inner = lead + "".join(items)
    return section_text[: m.start(1)] + inner + section_text[m.end(1) :]


def _section_segments(resume_tex: str):
    heads = list(re.finditer(r"\\section\{([^}]*)\}", resume_tex))
    if not heads:
        return None, []
    preamble = resume_tex[: heads[0].start()]
    segments = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(resume_tex)
        segments.append({"name": m.group(1).strip().lower(), "text": resume_tex[m.start() : end]})
    return preamble, segments


class AdditionError(ValueError):
    pass


ITEMIZE_RE = re.compile(r"\\begin\{itemize\}(.*?)\\end\{itemize\}", re.DOTALL)
LINE_BREAK_RE = re.compile(r"\\\\(\[[^\]]*\])?")


def _job_label(before: str) -> str:
    """Label for the job whose bullets follow `before`, e.g. 'AngelOne | February 2022 -- February 2026 | Senior SRE'.

    Uses the last two non-empty lines above the bullet list: the company/dates line and the title line.
    """
    lines = [ln for ln in before.splitlines() if ln.strip() and "\\section{" not in ln]
    parts = []
    for ln in lines[-2:]:
        text = " ".join(strip_latex(LINE_BREAK_RE.sub(" ", ln).replace("~", " ")).split())
        if text:
            parts.append(text)
    return " | ".join(parts) or "Untitled role"


def experience_jobs(resume_tex: str) -> list[dict]:
    """Bullet blocks in the Experience section, in order. Each block is one job."""
    _, segments = _section_segments(resume_tex)
    jobs = []
    for seg in segments:
        if seg["name"] not in EXPERIENCE_SECTION_NAMES:
            continue
        for m in ITEMIZE_RE.finditer(seg["text"]):
            jobs.append({"index": len(jobs), "label": _job_label(seg["text"][: m.start()])})
    return jobs


def add_bullets(resume_tex: str, additions: list[dict]) -> str:
    """Insert user-written bullets at the top of the chosen job's bullet list.

    Each addition is {"keyword", "job_index", "bullet"}. The bullet text is escaped for LaTeX
    and must contain its keyword. Nothing is generated here; the wording is the user's.
    """
    if not additions:
        return resume_tex
    jobs_count = len(experience_jobs(resume_tex))
    by_job: dict[int, list[str]] = {}
    for add in additions:
        idx = add["job_index"]
        if not 0 <= idx < jobs_count:
            raise AdditionError(f"Job {idx} does not exist in the Experience section.")
        bullet = " ".join(add["bullet"].split())
        if not _group_in_text(bullet, ALIAS_BY_LABEL.get(add["keyword"], [add["keyword"]])):
            raise AdditionError(f"The bullet for {add['keyword']} must contain that keyword.")
        by_job.setdefault(idx, []).append(latex_escape(bullet))

    preamble, segments = _section_segments(resume_tex)
    counter = {"n": 0}

    def insert(match: re.Match) -> str:
        n = counter["n"]
        counter["n"] += 1
        if n not in by_job:
            return match.group(0)
        new_items = "".join(f"\\item {text}\n" for text in by_job[n])
        return "\\begin{itemize}\n" + new_items + match.group(1) + "\\end{itemize}"

    out = [preamble]
    for seg in segments:
        if seg["name"] in EXPERIENCE_SECTION_NAMES:
            out.append(ITEMIZE_RE.sub(insert, seg["text"]))
        else:
            out.append(seg["text"])
    return "".join(out)


def _core_placement_plan(
    resume_tex: str, confirmed: list[str], placements: list[dict]
) -> tuple[dict[int, list[str]], dict[str, list[str]]]:
    """Split confirmed keywords into existing-line targets and new-line labels."""
    chosen = {p["keyword"]: p for p in placements if p.get("keyword") in confirmed}
    line_count = len(core_subsections(resume_tex))
    existing: dict[int, list[str]] = {}
    new: dict[str, list[str]] = {}
    for keyword in confirmed:
        place = chosen.get(keyword) or {}
        if place.get("subsection") is not None:
            idx = place["subsection"]
            if not 0 <= idx < line_count:
                raise AdditionError(f"Core Competencies line {idx} does not exist.")
            existing.setdefault(idx, []).append(keyword)
        else:
            label = " ".join((place.get("new_label") or "Other").split())[:60]
            new.setdefault(label, []).append(keyword)
    return existing, new


def tailor(
    resume_tex: str,
    jd_text: str,
    include_keywords: list[str] | None = None,
    reorder: bool = True,
    additions: list[dict] | None = None,
    placements: list[dict] | None = None,
) -> TailorResult:
    """Tailor a LaTeX resume against a job description without inventing content.

    include_keywords: gap keywords the user confirmed are true. Only keywords that
    are actually gaps are honored. Anything else is ignored.
    additions: bullets the user wrote for a keyword and a job (see add_bullets).
    A keyword with an addition counts as confirmed.
    placements: where each confirmed keyword goes in an existing Core Competencies list.
    {"keyword", "subsection": line index or None, "new_label": label for a new line}.
    {"keyword", "skip": True} keeps the keyword out of Core Competencies entirely.
    Confirmed keywords without a placement go to a new line labelled "Other".
    """
    covered, gaps = analyze(resume_tex, jd_text)
    added_keywords = [a["keyword"] for a in additions or []]
    extra = [k for k in (list(include_keywords or []) + added_keywords) if k in gaps]
    extra = list(dict.fromkeys(extra))
    # Keywords placed as "experience only" stay out of Core Competencies. They still rank for reordering.
    skipped = {p["keyword"] for p in placements or [] if p.get("skip")}
    ranked = covered + [k for k in extra if k not in covered]
    core_keywords = covered + [k for k in extra if k not in covered and k not in skipped]
    resume_tex = add_bullets(resume_tex, additions or [])

    preamble, segments = _section_segments(resume_tex)
    result = TailorResult(tex=resume_tex, matched=covered, gaps=gaps, core_keywords=core_keywords)

    if preamble is None:
        result.warnings.append("No \\section{} headings found. Resume returned unchanged.")
        return result

    has_core = any(seg["name"] == CORE_SECTION_NAME for seg in segments)
    # Confirmed gap keywords (not already in the resume) that must appear in Core Competencies.
    confirmed = [k for k in core_keywords if k not in covered]
    existing, new = _core_placement_plan(resume_tex, confirmed, placements or [])
    if has_core and confirmed:
        result.warnings.append(
            "Resume already has a Core Competencies section. No new one was added; "
            f"{len(confirmed)} confirmed keyword(s) were placed in it."
        )

    out = [preamble]
    core_inserted = has_core or not core_keywords
    for seg in segments:
        text = seg["text"]
        if reorder and ranked and seg["name"] in REORDER_SECTION_NAMES:
            new_text = _reorder_itemize_blocks(text, ranked)
            if new_text != text:
                result.reordered_sections.append(seg["name"])
            text = new_text
        if has_core and seg["name"] == CORE_SECTION_NAME and confirmed:
            text = place_in_core(text, existing, new)
        out.append(text)
        if not core_inserted and seg["name"] in SUMMARY_SECTION_NAMES:
            out.append(build_core_competencies(core_keywords))
            core_inserted = True

    tailored = "".join(out)
    if not core_inserted:
        block = build_core_competencies(core_keywords)
        if "\\end{document}" in tailored:
            tailored = tailored.replace("\\end{document}", block + "\n\\end{document}")
        else:
            tailored += block

    result.tex = tailored
    return result
