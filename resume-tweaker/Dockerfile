# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.12-slim-bookworm
FROM ${PYTHON_IMAGE}

# WITH_DOC=0 skips LibreOffice (legacy .doc support) for a much smaller image.
ARG WITH_DOC=1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=80

# WeasyPrint runtime libraries, plus LibreOffice when .doc support is enabled.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libharfbuzz0b \
      libharfbuzz-subset0 \
      fonts-dejavu-core \
      libcap2-bin \
 && if [ "$WITH_DOC" = "1" ]; then \
      apt-get install -y --no-install-recommends libreoffice-writer-nogui; \
    fi \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app

# Port 80 is privileged. Grant only the bind capability to the Python binary, so the server still runs as
# the unprivileged `app` user. Compose must not set no-new-privileges, which would block file capabilities.
RUN setcap 'cap_net_bind_service=+ep' "$(readlink -f "$(which python)")"

WORKDIR /opt/resume-tweaker

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app

USER app

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/healthz', timeout=4)" || exit 1

# One worker: sessions live in process memory (SPECIFICATION §10.1).
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
