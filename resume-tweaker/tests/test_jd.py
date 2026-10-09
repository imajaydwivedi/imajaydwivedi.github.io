import pytest

from app.errors import ServiceError
from app.jd import _validate_url, fetch_jd_url, html_to_text, sanitize_html, word_count
from app.jd import _check_host


def test_script_and_event_handlers_are_removed():
    cleaned = sanitize_html('<p onclick="x()">Hi</p><script>alert(1)</script><img src=x onerror=alert(2)>')
    assert "<script" not in cleaned.lower()
    assert "onclick" not in cleaned.lower()
    assert "onerror" not in cleaned.lower()
    assert "<img" not in cleaned.lower()
    assert "Hi" in cleaned


def test_javascript_urls_are_stripped():
    cleaned = sanitize_html('<a href="javascript:alert(1)">click</a>')
    assert "javascript:" not in cleaned.lower()


def test_formatting_tags_survive_sanitizing():
    cleaned = sanitize_html("<ul><li><strong>Python</strong></li></ul>")
    assert "<strong>Python</strong>" in cleaned
    assert "<li>" in cleaned


def test_html_to_text_keeps_list_items_on_separate_lines():
    text = html_to_text("<ul><li>Terraform</li><li>Kubernetes</li></ul>")
    assert "Terraform\nKubernetes" in text


@pytest.mark.parametrize(
    "url",
    ["file:///etc/passwd", "ftp://example.com/x", "http://user:pw@example.com/", "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data"],
)
def test_unsafe_urls_are_rejected(url):
    with pytest.raises(ServiceError):
        fetch_jd_url(url)


def test_private_addresses_are_blocked():
    with pytest.raises(ServiceError) as info:
        _check_host("http://127.0.0.1/job")
    assert info.value.code == "BLOCKED_ADDRESS"


def test_word_count():
    assert word_count("Senior engineer, five years.") == 4


def test_validate_url_accepts_https():
    assert _validate_url("https://example.com/jobs/1") == "https://example.com/jobs/1"
