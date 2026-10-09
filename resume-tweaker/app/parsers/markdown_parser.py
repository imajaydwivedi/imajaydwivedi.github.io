from ..errors import ServiceError


def parse_markdown(data: bytes) -> tuple[str, list[str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ServiceError(422, "PARSE_ERROR", "The Markdown file must be UTF-8 encoded.") from exc

    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    if not text.strip():
        raise ServiceError(422, "PARSE_ERROR", "The Markdown file is empty.")
    return text.strip() + "\n", []
