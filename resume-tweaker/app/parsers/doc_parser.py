"""Legacy .doc support: convert to .docx with LibreOffice, then reuse the DOCX parser."""

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..errors import ServiceError
from .docx_parser import parse_docx

CONVERT_TIMEOUT_SECONDS = 90


def _soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def parse_doc(data: bytes) -> tuple[str, list[str]]:
    binary = _soffice()
    if binary is None:
        raise ServiceError(503, "CONVERSION_UNAVAILABLE", "This build does not support .doc files. Save as .docx and retry.")

    with tempfile.TemporaryDirectory(prefix="rt-doc-") as workdir:
        work = Path(workdir)
        source = work / "input.doc"
        source.write_bytes(data)
        try:
            subprocess.run(
                [
                    binary,
                    "--headless",
                    "--norestore",
                    f"-env:UserInstallation=file://{work / 'profile'}",
                    "--convert-to",
                    "docx",
                    "--outdir",
                    str(work),
                    str(source),
                ],
                capture_output=True,
                timeout=CONVERT_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ServiceError(422, "PARSE_ERROR", "Converting the .doc file took too long.") from exc

        converted = work / "input.docx"
        if not converted.exists():
            raise ServiceError(422, "PARSE_ERROR", "Could not convert this .doc file. Try saving it as .docx.")
        return parse_docx(converted.read_bytes())
