"""FastAPI app. Stateless: every request carries the resume it needs."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .convert import ConvertError, capabilities, to_docx, to_pdf
from .tailor import AdditionError, analyze, experience_jobs, extract_jd_keywords, tailor

MAX_CHARS = 200_000
STATIC_DIR = Path(__file__).parent / "static"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

app = FastAPI(title="Resume Tailor (LaTeX)", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ResumeJD(BaseModel):
    resume_tex: str = Field(min_length=1, max_length=MAX_CHARS)
    jd_text: str = Field(min_length=1, max_length=MAX_CHARS)


class Addition(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)
    job_index: int = Field(ge=0, le=100)
    bullet: str = Field(min_length=1, max_length=300)


class TailorRequest(ResumeJD):
    include_keywords: list[str] = Field(default_factory=list, max_length=500)
    reorder: bool = True
    additions: list[Addition] = Field(default_factory=list, max_length=100)


class ResumeOnly(BaseModel):
    resume_tex: str = Field(min_length=1, max_length=MAX_CHARS)


class TexRequest(BaseModel):
    tex: str = Field(min_length=1, max_length=MAX_CHARS)


def _file(content: bytes, media_type: str, name: str) -> Response:
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


def _error(exc: ConvertError) -> Response:
    return Response(content=str(exc), status_code=422, media_type="text/plain")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/status")
def status() -> dict:
    return capabilities()


@app.post("/api/analyze")
def analyze_route(req: ResumeJD) -> dict:
    covered, gaps = analyze(req.resume_tex, req.jd_text)
    return {
        "jd_keyword_count": len(extract_jd_keywords(req.jd_text)),
        "covered": covered,
        "gaps": gaps,
    }


@app.post("/api/jobs")
def jobs_route(req: ResumeOnly) -> dict:
    return {"jobs": experience_jobs(req.resume_tex)}


@app.post("/api/tailor", response_model=None)
def tailor_route(req: TailorRequest):
    try:
        result = tailor(
            req.resume_tex,
            req.jd_text,
            include_keywords=req.include_keywords,
            reorder=req.reorder,
            additions=[a.model_dump() for a in req.additions],
        )
    except AdditionError as exc:
        return Response(content=str(exc), status_code=422, media_type="text/plain")
    return {
        "tex": result.tex,
        "covered": result.matched,
        "gaps": result.gaps,
        "core_keywords": result.core_keywords,
        "reordered_sections": result.reordered_sections,
        "warnings": result.warnings,
    }


@app.post("/api/pdf")
def pdf_route(req: TexRequest) -> Response:
    try:
        return _file(to_pdf(req.tex), "application/pdf", "resume.pdf")
    except ConvertError as exc:
        return _error(exc)


@app.post("/api/docx")
def docx_route(req: TexRequest) -> Response:
    try:
        return _file(to_docx(req.tex), DOCX_TYPE, "resume.docx")
    except ConvertError as exc:
        return _error(exc)
