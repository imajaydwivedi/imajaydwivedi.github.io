"""Fetch a .tex resume from a GitHub or Google Drive link.

Only GitHub and Google Drive hosts are allowed, so the server cannot be pointed at arbitrary URLs.
"""

import re
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlparse

MAX_BYTES = 200_000
TIMEOUT_SECONDS = 10
ALLOWED_HOSTS = {"github.com", "raw.githubusercontent.com", "drive.google.com"}
# Drive file downloads redirect to a Google content host, so redirects may land there too.
REDIRECT_SUFFIXES = (".googleusercontent.com",)
DRIVE_ID = re.compile(r"^[A-Za-z0-9_-]{10,200}$")


class RemoteError(ValueError):
    """The link is not supported, or the file could not be read."""


def _check_url(url: str) -> None:
    parts = urlparse(url)
    host = parts.hostname or ""
    if parts.scheme != "https" or not (host in ALLOWED_HOSTS or host.endswith(REDIRECT_SUFFIXES)):
        raise RemoteError("Only https links to GitHub or Google Drive are supported.")


def to_download_url(url: str) -> str:
    """Turn a GitHub or Google Drive file link into a URL that returns the raw file."""
    url = url.strip()
    _check_url(url)
    parts = urlparse(url)
    host = parts.hostname
    segs = [s for s in parts.path.split("/") if s]

    if host == "github.com":
        # /owner/repo/blob/branch/path/to/file.tex
        if len(segs) < 5 or segs[2] != "blob":
            raise RemoteError("GitHub link must point to a file, e.g. github.com/owner/repo/blob/main/resume.tex.")
        return "https://raw.githubusercontent.com/" + "/".join([segs[0], segs[1]] + segs[3:])

    if host == "raw.githubusercontent.com":
        if len(segs) < 4:
            raise RemoteError("Raw GitHub link must point to a file.")
        return url

    # Google Drive: /file/d/ID/view or open?id=ID
    if len(segs) >= 3 and segs[0] == "file" and segs[1] == "d":
        file_id = segs[2]
    else:
        file_id = parse_qs(parts.query).get("id", [""])[0]
    if not DRIVE_ID.match(file_id):
        raise RemoteError("Google Drive link must be a file link, e.g. drive.google.com/file/d/ID/view.")
    return f"https://drive.google.com/uc?export=download&id={file_id}"


class _CheckedRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects to hosts outside the allowlist."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_tex(url: str) -> str:
    download = to_download_url(url)
    opener = urllib.request.build_opener(_CheckedRedirect)
    request = urllib.request.Request(download, headers={"User-Agent": "resume-tweaker"})
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as res:
            content_type = res.headers.get_content_type()
            body = res.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RemoteError(f"Could not fetch the file (HTTP {exc.code}). Check that the link is correct and public.")
    except (urllib.error.URLError, OSError):
        raise RemoteError("Could not reach the link.")

    if len(body) > MAX_BYTES:
        raise RemoteError("File is too large to be a resume.")
    if content_type == "text/html":
        raise RemoteError("The link returned a web page, not a .tex file. "
                          "For Google Drive, share the file as 'Anyone with the link'.")
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        raise RemoteError("File is not UTF-8 text.")
