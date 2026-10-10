"""Convert the tailored LaTeX resume to PDF (xelatex) or DOCX (pandoc).

Both run in a temporary directory. xelatex gets -no-shell-escape, so it cannot run shell commands.
LaTeX and pandoc can still read local files that a .tex source points at, so the container's
read-only, non-root setup is the real boundary.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

PDF_ENGINES = ("xelatex", "pdflatex")
TIMEOUT_SECONDS = 60


class ConvertError(Exception):
    pass


def pdf_engine() -> str | None:
    for name in PDF_ENGINES:
        if shutil.which(name):
            return name
    return None


def capabilities() -> dict[str, bool]:
    return {"pdf": pdf_engine() is not None, "docx": shutil.which("pandoc") is not None}


def _run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired as exc:
        raise ConvertError("Conversion timed out.") from exc


def _without_section_numbers(tex: str) -> str:
    """Turn off numbering for section headings, unless the source already sets it."""
    setting = "\\setcounter{secnumdepth}{-1}"
    if "secnumdepth" in tex or "\\begin{document}" not in tex:
        return tex
    return tex.replace("\\begin{document}", setting + "\n\\begin{document}", 1)


def to_pdf(tex: str) -> bytes:
    engine = pdf_engine()
    if engine is None:
        raise ConvertError("No LaTeX engine (xelatex or pdflatex) is installed.")
    with tempfile.TemporaryDirectory(prefix="rt-pdf-") as tmp:
        (Path(tmp) / "resume.tex").write_text(_without_section_numbers(tex), encoding="utf-8")
        # -no-shell-escape stops \write18 from running shell commands.
        proc = _run(
            [engine, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "resume.tex"], tmp
        )
        pdf = Path(tmp) / "resume.pdf"
        if proc.returncode != 0 or not pdf.exists():
            lines = proc.stdout.decode("utf-8", "replace").splitlines()
            errors = [line for line in lines if line.startswith("!")][:5]
            raise ConvertError("LaTeX compile failed. " + (" | ".join(errors) or "See the log."))
        return pdf.read_bytes()


def to_docx(tex: str) -> bytes:
    if shutil.which("pandoc") is None:
        raise ConvertError("pandoc is not installed.")
    with tempfile.TemporaryDirectory(prefix="rt-docx-") as tmp:
        (Path(tmp) / "resume.tex").write_text(tex, encoding="utf-8")
        # --sandbox is not used: with pandoc 2.17 it also blocks reading pandoc's own DOCX template files.
        proc = _run(["pandoc", "-f", "latex", "-t", "docx", "-o", "resume.docx", "resume.tex"], tmp)
        out = Path(tmp) / "resume.docx"
        if proc.returncode != 0 or not out.exists():
            err = proc.stderr.decode("utf-8", "replace").strip()
            raise ConvertError("DOCX conversion failed. " + (err[:300] or "See the log."))
        return out.read_bytes()
