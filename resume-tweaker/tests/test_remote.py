import pytest
from fastapi.testclient import TestClient

from app import remote
from app.main import app
from app.remote import RemoteError, to_download_url

client = TestClient(app)


@pytest.mark.parametrize("link, expected", [
    ("https://github.com/imajaydwivedi/imajaydwivedi.github.io/blob/main/resume-tweaker/samples/dbre_postgres_sqlserver.tex",
     "https://raw.githubusercontent.com/imajaydwivedi/imajaydwivedi.github.io/main/resume-tweaker/samples/dbre_postgres_sqlserver.tex"),
    ("https://raw.githubusercontent.com/o/r/main/cv.tex",
     "https://raw.githubusercontent.com/o/r/main/cv.tex"),
    ("https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view?usp=sharing",
     "https://drive.google.com/uc?export=download&id=1AbCdEfGhIjKlMnOp"),
    ("https://drive.google.com/open?id=1AbCdEfGhIjKlMnOp",
     "https://drive.google.com/uc?export=download&id=1AbCdEfGhIjKlMnOp"),
])
def test_supported_links_map_to_raw_download(link, expected):
    assert to_download_url(link) == expected


@pytest.mark.parametrize("link", [
    "http://github.com/o/r/blob/main/cv.tex",          # not https
    "https://example.com/cv.tex",                      # host not allowed
    "https://169.254.169.254/latest/meta-data",        # cloud metadata address
    "https://github.com/o/r",                          # not a file link
    "https://drive.google.com/drive/folders/abc",      # folder, no file id
    "https://drive.google.com/uc?id=../../etc",        # malformed id
])
def test_unsupported_links_are_rejected(link):
    with pytest.raises(RemoteError):
        to_download_url(link)


def test_fetch_route_returns_tex(monkeypatch):
    monkeypatch.setattr("app.main.fetch_tex", lambda url: "\\documentclass{article}")
    r = client.post("/api/fetch", json={"url": "https://github.com/o/r/blob/main/cv.tex"})
    assert r.status_code == 200
    assert r.json() == {"tex": "\\documentclass{article}"}


def test_fetch_route_reports_bad_link():
    r = client.post("/api/fetch", json={"url": "https://example.com/cv.tex"})
    assert r.status_code == 422
    assert "GitHub or Google Drive" in r.text


def test_fetch_rejects_html_response(monkeypatch):
    class FakeResponse:
        headers = type("H", (), {"get_content_type": lambda self: "text/html"})()

        def read(self, n):
            return b"<html>sign in</html>"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeOpener:
        def open(self, request, timeout):
            return FakeResponse()

    monkeypatch.setattr(remote.urllib.request, "build_opener", lambda *handlers: FakeOpener())
    with pytest.raises(RemoteError, match="not a .tex file"):
        remote.fetch_tex("https://github.com/o/r/blob/main/cv.tex")


def test_fetch_rejects_oversized_file(monkeypatch):
    class FakeResponse:
        headers = type("H", (), {"get_content_type": lambda self: "text/plain"})()

        def read(self, n):
            return b"x" * n

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeOpener:
        def open(self, request, timeout):
            return FakeResponse()

    monkeypatch.setattr(remote.urllib.request, "build_opener", lambda *handlers: FakeOpener())
    with pytest.raises(RemoteError, match="too large"):
        remote.fetch_tex("https://github.com/o/r/blob/main/cv.tex")
