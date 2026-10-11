from fastapi.testclient import TestClient

from app.main import app

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

client = TestClient(app)
RESUME = (FIXTURES / "sample_resume.tex").read_text()
JD = (FIXTURES / "sample_jd.txt").read_text()


def test_index_serves_page():
    r = client.get("/")
    assert r.status_code == 200
    assert "Resume Tweaker" in r.text


def test_index_versions_static_assets():
    r = client.get("/")
    assert r.headers["cache-control"] == "no-cache"
    assert '/static/app.js?v=' in r.text
    assert '/static/style.css?v=' in r.text


def test_analyze_returns_covered_and_gaps():
    r = client.post("/api/analyze", json={"resume_tex": RESUME, "jd_text": JD})
    assert r.status_code == 200
    body = r.json()
    assert "Kubernetes" in body["gaps"]
    assert "Terraform" in body["covered"]
    assert body["jd_keyword_count"] == len(body["covered"]) + len(body["gaps"])


def test_tailor_default_excludes_gaps():
    r = client.post("/api/tailor", json={"resume_tex": RESUME, "jd_text": JD})
    body = r.json()
    assert "Kubernetes" not in body["core_keywords"]
    assert "\\section{Core Competencies}" in body["tex"]


def test_tailor_with_confirmed_gap():
    r = client.post("/api/tailor", json={"resume_tex": RESUME, "jd_text": JD, "include_keywords": ["Kubernetes"]})
    assert "Kubernetes" in r.json()["core_keywords"]


def test_rejects_empty_input():
    r = client.post("/api/analyze", json={"resume_tex": "", "jd_text": "x"})
    assert r.status_code == 422


def test_rejects_oversized_input():
    r = client.post("/api/analyze", json={"resume_tex": "x" * 200_001, "jd_text": "x"})
    assert r.status_code == 422


def test_status_reports_capabilities(monkeypatch):
    monkeypatch.setattr("app.main.capabilities", lambda: {"pdf": True, "docx": False})
    assert client.get("/api/status").json() == {"pdf": True, "docx": False}


def test_pdf_reports_missing_engine(monkeypatch):
    monkeypatch.setattr("app.convert.pdf_engine", lambda: None)
    r = client.post("/api/pdf", json={"tex": RESUME})
    assert r.status_code == 422
    assert "No LaTeX engine" in r.text


def test_docx_reports_missing_pandoc(monkeypatch):
    monkeypatch.setattr("app.convert.shutil.which", lambda name: None)
    r = client.post("/api/docx", json={"tex": RESUME})
    assert r.status_code == 422
    assert "pandoc is not installed" in r.text


def test_pdf_returns_pdf_bytes(monkeypatch):
    monkeypatch.setattr("app.main.to_pdf", lambda tex: b"%PDF-1.5 fake")
    r = client.post("/api/pdf", json={"tex": RESUME})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert 'filename="resume.pdf"' in r.headers["content-disposition"]


def test_docx_returns_docx_bytes(monkeypatch):
    monkeypatch.setattr("app.main.to_docx", lambda tex: b"PK fake")
    r = client.post("/api/docx", json={"tex": RESUME})
    assert r.status_code == 200
    assert "wordprocessingml" in r.headers["content-type"]
    assert 'filename="resume.docx"' in r.headers["content-disposition"]


def test_healthz():
    assert client.get("/healthz").json() == {"ok": True}


def test_section_numbers_are_turned_off_in_pdf_source():
    from app.convert import _without_section_numbers

    out = _without_section_numbers("\\documentclass{article}\n\\begin{document}\nHi\n\\end{document}")
    assert "\\setcounter{secnumdepth}{-1}\n\\begin{document}" in out
    # An existing setting is left alone.
    own = (Path(__file__).parents[1] / "samples" / "ajay_resume.tex").read_text()
    assert _without_section_numbers(own) == own


def test_jobs_endpoint_lists_experience_blocks():
    r = client.post("/api/jobs", json={"resume_tex": RESUME})
    assert r.status_code == 200
    jobs = r.json()["jobs"]
    assert len(jobs) == 1 and jobs[0]["index"] == 0


def test_tailor_with_additions():
    r = client.post("/api/tailor", json={
        "resume_tex": RESUME, "jd_text": JD,
        "additions": [{"keyword": "Kafka", "job_index": 0, "bullet": "Built Kafka pipelines for alerts"}],
    })
    assert r.status_code == 200
    assert "Kafka" in r.json()["core_keywords"]
    assert "Built Kafka pipelines for alerts" in r.json()["tex"]


def test_tailor_rejects_bad_addition():
    r = client.post("/api/tailor", json={
        "resume_tex": RESUME, "jd_text": JD,
        "additions": [{"keyword": "Kafka", "job_index": 0, "bullet": "Ran patching"}],
    })
    assert r.status_code == 422
    assert "must contain that keyword" in r.text
