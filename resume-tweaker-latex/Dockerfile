# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.13-slim-bookworm
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=80 \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache

# TeX Live for xelatex (PDF), pandoc for DOCX, and libcap2-bin for the port-80 capability below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      texlive-xetex \
      texlive-latex-recommended \
      texlive-latex-extra \
      texlive-fonts-recommended \
      pandoc \
      libcap2-bin \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app

# Port 80 is privileged. Grant only the bind capability to the Python binary, so the server still runs as
# the unprivileged `app` user. Compose must not set no-new-privileges, which would block file capabilities.
RUN setcap 'cap_net_bind_service=+ep' "$(readlink -f "$(which python)")"

WORKDIR /opt/resume-tailor

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app

USER app

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/healthz', timeout=4)" || exit 1

# One worker: the app keeps no state, so a single process is enough.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
