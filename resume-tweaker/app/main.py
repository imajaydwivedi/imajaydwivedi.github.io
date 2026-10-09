"""Resume Tweaker web service. Routes follow SPECIFICATION §7."""

import logging
import re
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .analyzer import analyze
from .config import settings
from .errors import ServiceError
from .jd import fetch_jd_url, html_to_text, sanitize_html, word_count
from .parsers import parse_resume
from .render.docx import render_docx
from .render.html import render_document
from .render.pdf import render_pdf
from .sessions import Session, store
from .tweaker import apply_keywords, extract_name

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("resume_tweaker")

STATIC_DIR = Path(__file__).parent / "static"
COOKIE_NAME = "rt_session"
MIN_JD_WORDS = 40
MAX_JD_CHARS = 200_000

UI_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
    "connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
)
# Previews render Markdown from an uploaded file, so they get the strictest policy: no scripts, no images.
PREVIEW_CSP = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
DOWNLOAD_TYPES = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "md": "text/markdown; charset=utf-8",
}

app = FastAPI(title="Resume Tweaker", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(ServiceError)
async def service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.middleware("http")
async def common_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    sid = getattr(request.state, "sid", None)
    if sid and request.cookies.get(COOKIE_NAME) != sid:
        response.set_cookie(
            COOKIE_NAME,
            sid,
            max_age=settings.session_ttl_min * 60,
            httponly=True,
            samesite="lax",
            path="/",
        )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


def _session(request: Request) -> Session:
    sid, session = store.get_or_create(request.cookies.get(COOKIE_NAME))
    request.state.sid = sid
    return session


def _filename_part(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return cleaned[:60] or fallback


def _require_resume(session: Session) -> None:
    if not session.resume_md:
        raise ServiceError(409, "NO_RESUME", "Upload your resume first.")


# ---------- Pages and health ----------


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html", headers={"Content-Security-Policy": UI_CSP})


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


# ---------- Resume ----------


@app.post("/api/resume")
def upload_resume(request: Request, file: UploadFile = File(...)) -> dict:
    session = _session(request)
    data = file.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise ServiceError(413, "FILE_TOO_LARGE", f"The resume must be {settings.max_upload_mb} MB or smaller.")
    if not data:
        raise ServiceError(422, "EMPTY_FILE", "The uploaded file is empty.")

    parsed = parse_resume(file.filename or "", data)
    session.set_resume(parsed.markdown, parsed.fmt)
    log.info("resume parsed format=%s bytes=%d", parsed.fmt, len(data))  # never log the content
    return {
        "name": extract_name(parsed.markdown),
        "format": parsed.fmt,
        "word_count": word_count(parsed.markdown),
        "warnings": parsed.warnings,
    }


@app.get("/api/resume/preview")
def preview_resume(request: Request) -> HTMLResponse:
    session = _session(request)
    _require_resume(session)
    return _html_preview(render_document(session.resume_md))


# ---------- Job description ----------


class JDUrlIn(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


class JDTextIn(BaseModel):
    html: str = Field(default="", max_length=MAX_JD_CHARS)
    text: str = Field(default="", max_length=MAX_JD_CHARS)


@app.post("/api/jd/url")
def jd_from_url(body: JDUrlIn, request: Request) -> dict:
    session = _session(request)
    title, text = fetch_jd_url(body.url)
    session.set_jd(text, title)
    return {"title": title, "word_count": word_count(text), "text_preview": text[:400]}


@app.post("/api/jd/text")
def jd_from_text(body: JDTextIn, request: Request) -> dict:
    session = _session(request)
    text = html_to_text(sanitize_html(body.html)) if body.html.strip() else body.text.strip()
    if not text:
        raise ServiceError(422, "EMPTY_JD", "Paste the job description first.")
    title = next((line.strip()[:80] for line in text.split("\n") if line.strip()), "")
    session.set_jd(text, title)
    return {"title": title, "word_count": word_count(text)}


# ---------- Analysis and tweak ----------


@app.post("/api/analyze")
def analyze_resume(request: Request) -> dict:
    session = _session(request)
    _require_resume(session)
    if not session.jd_text:
        raise ServiceError(409, "NO_JD", "Provide a job description first.")

    words = word_count(session.jd_text)
    if words < MIN_JD_WORDS:
        raise ServiceError(
            422,
            "JD_TOO_SHORT",
            f"The job description needs at least {MIN_JD_WORDS} words; found {words}. Check the input.",
        )

    analysis = analyze(session.resume_md, session.jd_text, settings.max_suggestions)
    session.set_analysis(analysis)
    everything = [s.key for s in analysis.suggestions]
    return {
        "match_before": analysis.match_before,
        "match_after_estimate": analysis.match_after(everything),
        "suggestions": [_suggestion_json(s) for s in analysis.suggestions],
        "covered": [_suggestion_json(s) for s in analysis.covered],
    }


def _suggestion_json(item) -> dict:
    return {"id": item.id, "term": item.term, "count": item.count, "score": item.score, "source": item.source}


class TweakIn(BaseModel):
    accepted_ids: list[str] = Field(default_factory=list, max_length=200)
    reorder: bool = True


@app.post("/api/tweak")
def tweak_resume(body: TweakIn, request: Request) -> dict:
    session = _session(request)
    _require_resume(session)
    if session.analysis is None:
        raise ServiceError(409, "NO_ANALYSIS", "Analyze the job description first.")

    by_id = {s.id: s for s in [*session.analysis.suggestions, *session.analysis.covered]}
    chosen = [by_id[sid] for sid in dict.fromkeys(body.accepted_ids) if sid in by_id]
    if not chosen and not body.reorder:
        raise ServiceError(422, "NO_SELECTION", "Select at least one keyword, or turn on bullet reordering.")

    result = apply_keywords(
        session.resume_md,
        [s.term for s in chosen],
        reorder=body.reorder,
        jd_terms=list(session.analysis.jd_terms),
    )
    match_after = session.analysis.match_after([s.key for s in chosen])
    session.set_tweak(result.markdown, result.added, result.marked_lines, match_after)
    return {
        "added": result.added,
        "reordered_sections": result.reordered_sections,
        "match_before": session.analysis.match_before,
        "match_after": match_after,
    }


@app.get("/api/tweaked/preview")
def preview_tweaked(request: Request) -> HTMLResponse:
    session = _session(request)
    if not session.tweaked_md:
        raise ServiceError(404, "NOT_FOUND", "Tweak the resume first.")
    return _html_preview(render_document(session.tweaked_md, session.marked_lines))


@app.get("/api/download/{which}/{fmt}")
def download(
    which: Literal["original", "tweaked"],
    fmt: Literal["pdf", "docx", "md"],
    request: Request,
) -> Response:
    session = _session(request)
    markdown = session.resume_md if which == "original" else session.tweaked_md
    if not markdown:
        raise ServiceError(404, "NOT_FOUND", "Nothing to download yet.")

    name = _filename_part(extract_name(markdown), "Resume")
    slug = "original" if which == "original" else _filename_part(session.jd_title, "tweaked")
    filename = f"{name}_Resume_{slug}.{fmt}"

    if fmt == "pdf":
        content = render_pdf(markdown)
    elif fmt == "docx":
        content = render_docx(markdown)
    else:
        content = markdown.encode("utf-8")

    return Response(
        content=content,
        media_type=DOWNLOAD_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _html_preview(document: str) -> HTMLResponse:
    return HTMLResponse(document, headers={"Content-Security-Policy": PREVIEW_CSP})
