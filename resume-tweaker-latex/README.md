# Resume Tailor (LaTeX)

A small local web app that tailors a LaTeX resume to a job description. It uses Manisha's
rule-based approach: no LLM, no invented skills, and nothing is added unless you confirm it.

## What it does

1. **Analyze.** Finds catalog keywords (178 entries, from Manisha's `help-from-manisha.txt`) in the job description. Splits them into:
   - *Already in your resume*: included automatically.
   - *Missing*: unticked by default. Tick only what is true of you.
2. **Build.** Produces a tailored `.tex`:
   - Adds a **Core Competencies** section after the Summary, built from the keywords you accepted.
   - Reorders bullets in Skills and Experience so the most relevant ones come first. Wording, job order, and headings never change.
   - **Fit into experience:** for each missing keyword you tick, pick a job and write one bullet describing work you did. The tool inserts your wording as written, escaped for LaTeX. It must contain its keyword. The tool never writes bullets itself.
3. **Output.** Download `.tex`, `.pdf`, or `.docx`, or copy the `.tex` text.

## Run it (container)

```bash
cd resume-tweaker-latex           # this folder
docker compose up -d --build
```

Open http://localhost:8080. The app listens on port 80 inside the container, and compose maps host 8080 to it.

```bash
docker compose logs -f           # logs
docker compose down              # stop
```

The image includes TeX Live (xelatex) and pandoc, so the **.pdf** and **.docx** buttons work out of the box.
The container runs as a non-root user with a read-only filesystem; `/tmp` is the only writable place.

By default, compose binds the port to `127.0.0.1`, so only your machine can reach it. To allow other devices on
your network, change `"127.0.0.1:8080:80"` to `"8080:80"` in `docker-compose.yml`.

## Run it (without Docker)

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app          # http://127.0.0.1:8000
```

Without TeX and pandoc installed, only the **.tex** download and **Copy** buttons appear.

Tests:

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

## Layout

```
Dockerfile, docker-compose.yml
app/
  keywords.py     catalog, copied verbatim from Manisha's file
  tailor.py       matching, reorder, Core Competencies, LaTeX escaping
  convert.py      PDF (xelatex, -no-shell-escape) and DOCX (pandoc) conversion, 60s timeout
  main.py         FastAPI: /api/analyze, /api/tailor, /api/pdf, /api/docx, /api/status, /healthz
  static/         index.html, style.css, app.js (vanilla, no CDN)
tests/            pytest suite and LaTeX fixtures
```

The API is stateless. Each request carries its own resume and job description, and nothing is stored on the server.

## Changes from Manisha's script

Her matching rules, reorder logic, and Core Competencies format are kept. Four small changes:

- `\%` (an escaped percent sign) is no longer treated as the start of a LaTeX comment.
- `HA`, `DR`, and `ML` now match case-sensitively, like `Go` and `R`. This stops prose such as "Dr. Patel" from matching Disaster Recovery.
- If the resume already has a Core Competencies section, a second one is not added. A warning is shown instead.
- Reordered bullets keep their indentation.

## Known limits

- Reordering uses a regex over `\begin{itemize}...\end{itemize}`. Nested lists are not handled, and nested `\item`s would be reordered as if they were top-level.
- Keyword matching is literal. "k8s" will not match "Kubernetes" unless the alias exists in the catalog.
- `Hiring`, `Monitoring`, and similar generic words are in the catalog, so they can show up as gaps. Leave them unticked if they don't describe you.
- PDF and DOCX conversion were tested inside the container with the sample resume (2-page PDF, valid DOCX). Layout is the pdf template's; the DOCX drops some layout such as right-aligned dates.

## Security

LaTeX and pandoc can read local files when a `.tex` source points at them. The container limits what they can reach:
it runs as a non-root user, the root filesystem is read-only, and it holds no secrets. xelatex runs with `-no-shell-escape`.
Keep the port bound to `127.0.0.1` unless you have a reason to expose it.
