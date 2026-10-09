from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def resume_md() -> str:
    return (FIXTURES / "sample_resume.md").read_text(encoding="utf-8")


@pytest.fixture
def jd_text() -> str:
    return (FIXTURES / "sample_jd.txt").read_text(encoding="utf-8")
