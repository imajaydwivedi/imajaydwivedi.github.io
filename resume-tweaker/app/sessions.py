"""In-memory session store (SPECIFICATION §7 and §9). Nothing is written to disk."""

import re
import secrets
import threading
import time
from dataclasses import dataclass, field

from .analyzer import Analysis
from .config import settings

_SID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")


@dataclass
class Session:
    resume_md: str = ""
    resume_format: str = ""
    jd_text: str = ""
    jd_title: str = ""
    analysis: Analysis | None = None
    tweaked_md: str = ""
    marked_lines: frozenset[str] = frozenset()
    added: list[str] = field(default_factory=list)
    match_after: float = 0.0
    last_seen: float = field(default_factory=time.monotonic)

    def set_resume(self, markdown: str, fmt: str) -> None:
        self.resume_md = markdown
        self.resume_format = fmt
        self.analysis = None
        self.clear_tweak()

    def set_jd(self, text: str, title: str) -> None:
        self.jd_text = text
        self.jd_title = title
        self.analysis = None
        self.clear_tweak()

    def set_analysis(self, analysis: Analysis) -> None:
        self.analysis = analysis
        self.clear_tweak()

    def set_tweak(self, markdown: str, added: list[str], marked: frozenset[str], match_after: float) -> None:
        self.tweaked_md = markdown
        self.added = added
        self.marked_lines = marked
        self.match_after = match_after

    def clear_tweak(self) -> None:
        self.tweaked_md = ""
        self.added = []
        self.marked_lines = frozenset()
        self.match_after = 0.0


class SessionStore:
    def __init__(self, ttl_minutes: int, max_sessions: int):
        self._ttl = ttl_minutes * 60
        self._max = max_sessions
        self._data: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get_or_create(self, sid: str | None) -> tuple[str, Session]:
        with self._lock:
            now = time.monotonic()
            self._expire(now)
            if sid and _SID_RE.match(sid) and sid in self._data:
                session = self._data[sid]
                session.last_seen = now
                return sid, session

            sid = secrets.token_urlsafe(24)
            self._data[sid] = Session()
            self._evict_oldest()
            return sid, self._data[sid]

    def _expire(self, now: float) -> None:
        for sid in [k for k, v in self._data.items() if now - v.last_seen > self._ttl]:
            del self._data[sid]

    def _evict_oldest(self) -> None:
        while len(self._data) > self._max:
            oldest = min(self._data, key=lambda k: self._data[k].last_seen)
            del self._data[oldest]


store = SessionStore(settings.session_ttl_min, settings.max_sessions)
