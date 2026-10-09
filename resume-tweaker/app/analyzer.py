"""Keyword analysis (SPECIFICATION §6). Deterministic and offline.

Two sources of keywords feed the result:
  1. The curated catalog (app/catalog.py), which is precise and knows synonyms.
  2. Phrase candidates mined from the JD by frequency, which catch terms the catalog lacks.

Catalog keywords are split into *missing* (suggested for the user to add) and *covered*
(already in the resume, so they can be listed in Core Competencies without inventing anything).
"""

import math
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .catalog import Group, group_count, group_in_text, groups_in_text

DATA_DIR = Path(__file__).parent / "data"
TARGET_SIZE = 40  # number of top JD keywords used for the match score

URL_OR_EMAIL_RE = re.compile(r"https?://\S+|\S+@\S+")
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#./-]*[a-z0-9+#]|[a-z0-9]")
# Phrases never cross these, so "Python, SQL" does not become one term.
CLAUSE_SPLIT_RE = re.compile(r"[,;:!?()\[\]{}|•·\"“”]|\.\s|\s-\s|\s{3,}")
HYPHENATED_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")
REQ_HEADING_RE = re.compile(
    r"\b(requirements?|responsibilities|qualifications?|what you('|’)ll (do|need|bring)"
    r"|must[- ]have|skills|you have|what we('|’)re looking for)\b",
    re.IGNORECASE,
)
# Matched at the start of a line: "Benefits: ..." closes the requirements section.
OTHER_HEADING_RE = re.compile(
    r"(about (us|the company)|benefits|perks|compensation|salary|who we are|equal opportunity|diversity)\b",
    re.IGNORECASE,
)


def _load_lines(name: str) -> list[str]:
    lines = (DATA_DIR / name).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


STOPWORDS = frozenset(word.lower() for word in _load_lines("stopwords.txt"))
GENERIC = frozenset(word.lower() for word in _load_lines("generic_terms.txt"))
# Lower-case key -> canonical display form, e.g. "postgresql" -> "PostgreSQL".
TECH = {term.lower(): term for term in _load_lines("tech_terms.txt")}


@dataclass(frozen=True)
class Suggestion:
    id: str
    key: str  # lower-case identity used for matching
    term: str  # display text, also what gets written into the resume
    count: int  # occurrences in the JD
    score: int  # relative relevance, 0-100
    source: str  # "catalog" or "phrase"


@dataclass(frozen=True)
class Analysis:
    suggestions: list[Suggestion]  # missing from the resume; the user decides
    covered: list[Suggestion]  # catalog keywords the resume already contains
    target_terms: frozenset[str]  # keys of the top JD keywords (catalog + phrases)
    missing_keys: frozenset[str]  # keys of suggestions
    present_count: int  # target keys the resume already covers
    jd_terms: tuple[str, ...] = field(default_factory=tuple)  # used to rank bullets when reordering

    @property
    def match_before(self) -> float:
        return self._percent(self.present_count)

    def match_after(self, accepted_terms: Iterable[str]) -> float:
        newly_covered = {term.lower() for term in accepted_terms} & self.missing_keys & self.target_terms
        return self._percent(self.present_count + len(newly_covered))

    def _percent(self, count: int) -> float:
        if not self.target_terms:
            return 0.0
        return round(100 * count / len(self.target_terms), 1)


@dataclass(frozen=True)
class _Scored:
    key: str
    display: str
    count: int
    raw: float
    source: str


def analyze(resume_md: str, jd_text: str, max_suggestions: int) -> Analysis:
    resume_lower = resume_md.lower()

    # 1. Catalog keywords: exact, synonym-aware, split into covered and missing.
    catalog_items: list[_Scored] = []
    covered: list[_Scored] = []
    missing_catalog: list[_Scored] = []
    catalog_groups: list[Group] = _drop_nested_labels(groups_in_text(jd_text))
    for group in catalog_groups:
        count = group_count(group, jd_text)
        raw = (1 + math.log(count)) * 1.4
        item = _Scored(key=group.label.lower(), display=group.label, count=count, raw=raw, source="catalog")
        catalog_items.append(item)
        (covered if group_in_text(group, resume_md) else missing_catalog).append(item)

    # 2. Phrase candidates, minus anything the catalog already expresses.
    catalog_keys = [item.key for item in catalog_items]
    catalog_aliases = [alias.lower() for group in catalog_groups for alias in group.aliases]
    phrases = [
        item
        for item in _rank_phrases(jd_text)
        if not _overlaps(item.key, catalog_keys + catalog_aliases)
    ]

    ranked = sorted(catalog_items + phrases, key=lambda item: (-item.raw, item.key))
    if not ranked:
        return Analysis(suggestions=[], covered=[], target_terms=frozenset(), missing_keys=frozenset(), present_count=0)

    target_phrases = phrases[:TARGET_SIZE]
    target_keys = {item.key for item in catalog_items} | {item.key for item in target_phrases}
    covered_keys = {item.key for item in covered}
    present_count = sum(
        1
        for key in target_keys
        if key in covered_keys or (key not in catalog_keys and contains_term(key, resume_lower))
    )

    # 3. Missing suggestions: catalog gaps and phrases the resume does not contain, de-duplicated.
    top_raw = ranked[0].raw
    suggestions: list[Suggestion] = []
    kept_keys: list[str] = []
    for item in sorted(missing_catalog + phrases, key=lambda i: (-i.raw, i.key)):
        if item.source == "phrase" and (contains_term(item.key, resume_lower) or _overlaps(item.key, kept_keys)):
            continue
        kept_keys.append(item.key)
        suggestions.append(_to_suggestion(item, top_raw))
        if len(suggestions) >= max_suggestions:
            break

    covered_list = [_to_suggestion(item, top_raw) for item in sorted(covered, key=lambda i: (-i.raw, i.key))]
    jd_terms = tuple(item.display for item in catalog_items)

    return Analysis(
        suggestions=suggestions,
        covered=covered_list,
        target_terms=frozenset(target_keys),
        missing_keys=frozenset(item.key for item in suggestions),
        present_count=present_count,
        jd_terms=jd_terms,
    )


def _drop_nested_labels(groups: list[Group]) -> list[Group]:
    # "Reliability Engineering" adds nothing when "Site Reliability Engineering" is also matched.
    labels = [g.label.lower() for g in groups]
    return [g for g in groups if not any(
        other != g.label.lower() and contains_term(g.label.lower(), other) for other in labels
    )]


def contains_term(needle: str, haystack_lower: str) -> bool:
    """Whole-word, case-insensitive containment. `haystack_lower` must already be lower-cased."""
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack_lower) is not None


def _to_suggestion(item: _Scored, top_raw: float) -> Suggestion:
    return Suggestion(
        id=_slug(item.key),
        key=item.key,
        term=item.display,
        count=item.count,
        score=round(100 * item.raw / top_raw),
        source=item.source,
    )


def _rank_phrases(jd_text: str) -> list[_Scored]:
    # key -> [occurrences, occurrences in requirement sections, occurrences near the top]
    stats: dict[str, list[int]] = {}
    for key, in_requirements, near_top in _occurrences(jd_text):
        row = stats.setdefault(key, [0, 0, 0])
        row[0] += 1
        row[1] += in_requirements
        row[2] += near_top

    scored = []
    for key, (count, in_requirements, near_top) in stats.items():
        is_tech = key in TECH
        if not is_tech and count < 2 and in_requirements == 0:
            continue  # a single mention of a non-technical phrase is usually noise

        raw = 1 + math.log(count)
        if is_tech:
            raw *= 1.4
        elif " " not in key:
            raw *= 0.6  # single non-technical words ("build", "code") are weak keywords
        elif any(token in GENERIC for token in key.split()):
            raw *= 0.3
        if in_requirements or near_top:
            raw *= 1.2
        scored.append(_Scored(key=key, display=TECH.get(key, key), count=count, raw=raw, source="phrase"))

    scored.sort(key=lambda item: (-item.raw, item.key))
    return scored


def _occurrences(jd_text: str) -> Iterator[tuple[str, bool, bool]]:
    lines = _normalize(jd_text).split("\n")
    total = max(len(lines), 1)
    in_requirements = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # A short requirements heading opens the section; a line starting with another heading closes it.
        if len(stripped) < 60 and REQ_HEADING_RE.search(stripped):
            in_requirements = True
        elif OTHER_HEADING_RE.match(stripped):
            in_requirements = False
        near_top = index < total * 0.25

        for clause in CLAUSE_SPLIT_RE.split(stripped):
            tokens = TOKEN_RE.findall(clause)
            for n in (1, 2, 3):
                for start in range(len(tokens) - n + 1):
                    gram = tokens[start : start + n]
                    if _valid(gram):
                        yield " ".join(gram), in_requirements, near_top


def _valid(gram: list[str]) -> bool:
    if gram[0] in STOPWORDS or gram[-1] in STOPWORDS:
        return False
    if len(gram) > 1 and any(token in STOPWORDS for token in gram):
        return False
    if all(token in GENERIC or token in STOPWORDS for token in gram):
        return False
    text = " ".join(gram)
    if not any(ch.isalpha() for ch in text):
        return False
    if len(gram) > 1 and any(not any(ch.isalpha() for ch in token) for token in gram):
        return False  # "5+ years", "2 tb"
    if len(gram) == 1 and len(text) < 2 and text not in TECH:
        return False
    return True


def _normalize(text: str) -> str:
    text = text.lower().replace("’", "'").replace("–", "-").replace("—", "-")
    text = URL_OR_EMAIL_RE.sub(" ", text)
    # "Terraform-managed" -> "terraform managed", but keep hyphenated known terms such as "scikit-learn".
    return HYPHENATED_RE.sub(lambda m: m.group(0) if m.group(0) in TECH else m.group(0).replace("-", " "), text)


def _overlaps(key: str, kept: list[str]) -> bool:
    # Drop near-duplicates such as "aws" next to "aws lambda"; the higher-ranked term wins.
    return any(contains_term(key, other) or contains_term(other, key) for other in kept)


def _slug(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", key).strip("-")
