"""Job description intake: SSRF-safe URL fetching and HTML sanitizing (SPECIFICATION §4.2, §9)."""

import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

import httpx
import nh3
from bs4 import BeautifulSoup

from .errors import ServiceError

MAX_FETCH_BYTES = 2 * 1024 * 1024
FETCH_TIMEOUT_SECONDS = 10
MAX_REDIRECTS = 5
MAX_URL_LENGTH = 2048
USER_AGENT = "Mozilla/5.0 (compatible; ResumeTweaker/0.1; +https://github.com/imajaydwivedi)"

ALLOWED_TAGS = {"p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "h1", "h2", "h3", "h4", "a", "span"}
ALLOWED_ATTRIBUTES = {"a": {"href"}}
BLOCK_TAGS = ["p", "li", "ul", "ol", "div", "br", "h1", "h2", "h3", "h4", "tr", "section", "article", "table"]
NOISE_TAGS = ["script", "style", "noscript", "svg", "form", "nav", "header", "footer", "iframe", "button", "template"]


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w[\w'-]*\b", text))


def sanitize_html(html: str) -> str:
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
    )


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return _soup_to_text(soup)


def fetch_jd_url(url: str) -> tuple[str, str]:
    """Return (title, text) for a public job posting. Raises ServiceError on any failure."""
    current = _validate_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"}

    with httpx.Client(timeout=FETCH_TIMEOUT_SECONDS, headers=headers, follow_redirects=False) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _check_host(current)
            with client.stream("GET", current) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ServiceError(502, "FETCH_FAILED", "The page redirected without a destination.")
                    current = _validate_url(urljoin(current, location))
                    continue

                if response.status_code >= 400:
                    raise ServiceError(502, "FETCH_FAILED", f"The job page returned HTTP {response.status_code}.")

                content_type = response.headers.get("content-type", "").lower()
                if "html" not in content_type and "text" not in content_type:
                    raise ServiceError(422, "UNSUPPORTED_CONTENT", "The URL did not return a web page.")

                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_FETCH_BYTES:
                        raise ServiceError(413, "TOO_LARGE", "The job page is larger than 2 MB.")

                html = bytes(body).decode(response.encoding or "utf-8", errors="replace")
                return _extract_posting(html)

    raise ServiceError(502, "FETCH_FAILED", "Too many redirects.")


def _validate_url(url: str) -> str:
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise ServiceError(422, "INVALID_URL", "That URL is too long.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ServiceError(422, "INVALID_URL", "Enter a full http:// or https:// address.")
    if parsed.username or parsed.password:
        raise ServiceError(422, "INVALID_URL", "URLs with embedded credentials are not allowed.")
    return url


def _check_host(url: str) -> None:
    """Refuse hosts that resolve to private, loopback, link-local or otherwise non-public addresses."""
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ServiceError(502, "FETCH_FAILED", "The job page host could not be resolved.") from exc

    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise ServiceError(422, "BLOCKED_ADDRESS", "That address is not a public web server.")


def _extract_posting(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    elif soup.title and soup.title.string:
        title = soup.title.string.strip()

    for tag in soup(NOISE_TAGS):
        tag.decompose()

    # Prefer the most content-rich container: <article>, <main>, or the whole body.
    candidates = [node for node in (soup.find("article"), soup.find("main"), soup.body) if node is not None]
    root = max(candidates, key=lambda node: len(node.get_text(" ")), default=soup)
    return title, _soup_to_text(root)


def _soup_to_text(node) -> str:
    for br in node.find_all("br"):
        br.replace_with("\n")
    for block in node.find_all(BLOCK_TAGS):
        block.insert_before("\n")
        block.insert_after("\n")
    text = node.get_text("")
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()
