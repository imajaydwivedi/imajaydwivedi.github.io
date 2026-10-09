"""Runtime settings, read from environment variables (see SPECIFICATION §9)."""

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    port: int = _int("PORT", 80)
    max_upload_mb: int = _int("MAX_UPLOAD_MB", 5)
    session_ttl_min: int = _int("SESSION_TTL_MIN", 60)
    max_suggestions: int = _int("MAX_SUGGESTIONS", 30)
    max_sessions: int = 50
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


settings = Settings()
