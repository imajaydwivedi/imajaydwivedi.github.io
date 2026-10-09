"""Curated keyword catalog with synonym groups (adapted from Manisha's rule-based tailor).

A group matches when any of its aliases appears as a whole word. Synonyms matter: a JD asking
for "Golang" is satisfied by a resume that says "Go". Short all-caps aliases (DR, ETL, IAM) and
ambiguous words (Go, R) are matched case-sensitively so ordinary prose does not trigger them.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "data" / "keyword_groups.json"


@dataclass(frozen=True)
class Group:
    label: str
    aliases: tuple[str, ...]


def _load():
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    explicit = set(data["case_sensitive_aliases"])
    groups = tuple(Group(g["label"], tuple(g["aliases"])) for g in data["groups"])
    return groups, explicit


GROUPS, _EXPLICIT_CASE_SENSITIVE = _load()


def _is_case_sensitive(alias: str) -> bool:
    return alias in _EXPLICIT_CASE_SENSITIVE or (alias.isupper() and len(alias) <= 5)


_PATTERNS: dict[str, list[re.Pattern]] = {
    group.label: [
        re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])",
            0 if _is_case_sensitive(alias) else re.IGNORECASE,
        )
        for alias in group.aliases
    ]
    for group in GROUPS
}


def group_count(group: Group, text: str) -> int:
    """Number of whole-word alias occurrences of the group in the text."""
    return sum(len(pattern.findall(text)) for pattern in _PATTERNS[group.label])


def group_in_text(group: Group, text: str) -> bool:
    return any(pattern.search(text) for pattern in _PATTERNS[group.label])


def groups_in_text(text: str) -> list[Group]:
    return [group for group in GROUPS if group_in_text(group, text)]
