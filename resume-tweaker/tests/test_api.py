import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def uploaded(resume_md):
    response = client.post("/api/resume", files={"file": ("resume.md", resume_md.encode(), "text/markdown")})
    assert response.status_code == 200, response.text
    return response.json()


def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_index_serves_ui_with_csp():
    response = client.get("/")
    assert response.status_code == 200
    assert "Resume Tweaker" in response.text
    assert "script-src 'self'" in response.headers["content-security-policy"]


def test_upload_returns_name_and_format(uploaded):
    assert uploaded["name"] == "Jane Doe"
    assert uploaded["format"] == "md"
    assert uploaded["word_count"] > 20


def test_upload_rejects_unsupported_type():
    response = client.post("/api/resume", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_analyze_requires_jd_first(uploaded):
    fresh = TestClient(app)
    fresh.post("/api/resume", files={"file": ("resume.md", b"# Jane\n\n## Skills\n\n- Python\n", "text/markdown")})
    response = fresh.post("/api/analyze")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NO_JD"


def test_short_jd_is_rejected(uploaded):
    client.post("/api/jd/text", json={"text": "Engineer needed."})
    response = client.post("/api/analyze")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "JD_TOO_SHORT"


def test_full_flow_upload_analyze_tweak_download(uploaded, jd_text):
    assert client.post("/api/jd/text", json={"text": jd_text}).status_code == 200

    analysis = client.post("/api/analyze").json()
    assert analysis["suggestions"], "expected suggestions"
    assert 0 <= analysis["match_before"] <= 100

    ids = [s["id"] for s in analysis["suggestions"]]
    keep = [i for i in ids if i != ids[0]]  # uncheck the first suggestion
    tweak = client.post("/api/tweak", json={"accepted_ids": keep})
    assert tweak.status_code == 200, tweak.text
    body = tweak.json()
    assert analysis["suggestions"][0]["term"] not in body["added"]

    preview = client.get("/api/tweaked/preview")
    assert preview.status_code == 200
    assert "<mark>" in preview.text
    assert "Core Competencies" in preview.text
    assert "default-src 'none'" in preview.headers["content-security-policy"]

    for fmt, signature in [("md", b"# Jane Doe"), ("pdf", b"%PDF"), ("docx", b"PK")]:
        download = client.get(f"/api/download/tweaked/{fmt}")
        assert download.status_code == 200, fmt
        assert download.content.startswith(signature), fmt
        assert "attachment" in download.headers["content-disposition"]


def test_tweak_with_no_selection_is_rejected(uploaded, jd_text):
    client.post("/api/jd/text", json={"text": jd_text})
    client.post("/api/analyze")
    response = client.post("/api/tweak", json={"accepted_ids": [], "reorder": False})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "NO_SELECTION"


def test_tweaked_preview_404_before_tweak(uploaded):
    fresh = TestClient(app)
    fresh.post("/api/resume", files={"file": ("resume.md", b"# Jane\n\n## Skills\n\n- Python\n", "text/markdown")})
    assert fresh.get("/api/tweaked/preview").status_code == 404


def test_preview_escapes_raw_html_in_uploads():
    hostile = "# Jane\n\n<script>alert(1)</script>\n\n## Skills\n\n- Python\n"
    fresh = TestClient(app)
    fresh.post("/api/resume", files={"file": ("resume.md", hostile.encode(), "text/markdown")})
    preview = fresh.get("/api/resume/preview")
    assert "<script>alert(1)</script>" not in preview.text
