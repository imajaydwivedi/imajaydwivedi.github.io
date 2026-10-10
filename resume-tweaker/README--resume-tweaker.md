# Resume Tweaker

A local web app that tailors a LaTeX resume to a job description. It uses Manisha's rule-based approach: no LLM, no invented skills, and nothing is added unless you confirm it.

## What it does

1. **Analyze.** Finds keywords from the catalog (178 entries, taken from Manisha's `help-from-manisha.txt`) in the job description, and splits them into:
   - *Already in your resume*: included automatically.
   - *Missing*: unticked by default. Tick only what is true of you.
2. **Fit into experience (optional).** For each missing keyword you tick, pick a job and write one bullet describing work you actually did. The tool inserts your wording as written, escaped for LaTeX. The bullet must contain its keyword. The tool never writes bullets itself. Leaving a box empty adds nothing to the resume.
3. **Build.** Produces the tailored `.tex`:
   - Adds a **Core Competencies** section after the summary (`Profile`, `Professional Summary`, or `Summary`), built from the keywords you accepted.
   - Reorders bullets in Skills and Experience so the most relevant ones come first. Wording, job order, and headings never change.
4. **Output.** Download `.tex`, `.pdf`, or `.docx`, or copy the `.tex` text.

The PDF and DOCX buttons appear only when the server has the converters. The container includes them.

## Run it (container)

```bash
cd resume-tweaker
docker compose up -d --build
```

Open http://localhost:8080. The app listens on port 80 inside the container, and compose maps host port 8080 to it.

```bash
docker compose logs -f           # logs
docker compose down              # stop and remove the container
docker ps --filter name=resume-tweaker   # check status (should say "healthy")
```

The container is named `resume-tweaker`, and its image is `resume-tweaker:latest`.

- It runs as a non-root user with a read-only filesystem. `/tmp` is the only writable location.
- Compose binds the port to `127.0.0.1`, so only this machine can reach it. To allow other devices on your network, change `"127.0.0.1:8080:80"` to `"8080:80"` in `docker-compose.yml`.

## Run it (without Docker)

Tested with Python 3.14, the version the pinned packages were installed under. The PDF and DOCX buttons also need `xelatex` and `pandoc` on your PATH.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app                  # http://127.0.0.1:8000
```

Without TeX and pandoc, only the **.tex** download and **Copy** buttons appear.

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

The suite has 36 tests. It covers keyword matching, the no-invention rule, bullet insertion, job labels, and the API endpoints. The PDF and DOCX conversions are checked through the running container, not by the tests.

## Sample resume

`samples/ajay_resume.tex` is the current resume in the Manisha-style layout. Paste it into the page to try the tool.

- `samples/output/ajay_resume.pdf` and `.docx` are the outputs generated from it.
- `samples/ajay_resume_v1.tex` is the previous layout, kept for reference.

## Layout

```
Dockerfile, docker-compose.yml, requirements*.txt
app/
  keywords.py     keyword catalog, copied verbatim from Manisha's file
  tailor.py       matching, bullet insertion, reorder, Core Competencies, job labels, LaTeX escaping
  convert.py      PDF (xelatex, -no-shell-escape) and DOCX (pandoc) conversion, 60 s timeout
  main.py         FastAPI: /api/analyze, /api/jobs, /api/tailor, /api/pdf, /api/docx, /api/status, /healthz
  static/         index.html, style.css, app.js (vanilla, no CDN)
tests/            pytest suite and LaTeX fixtures
samples/          sample resume and generated outputs
```

The API is stateless. Each request carries its own resume and job description, and nothing is stored on the server.

## Changes from Manisha's script

Her matching rules, reorder logic, and Core Competencies format are kept. Small changes:

- `\%` (an escaped percent sign) is no longer treated as the start of a LaTeX comment.
- `HA`, `DR`, and `ML` match case-sensitively, like `Go` and `R`. This stops prose such as "Dr. Patel" from matching Disaster Recovery.
- `strip_latex` puts spaces around unwrapped `\textbf{}` and `\textit{}` text, so a command is not fused with the word after it.
- If the resume already has a Core Competencies section, a second one is not added. A warning is shown instead.
- Reordered bullets keep their indentation.
- Summary headings `Profile`, `Professional Summary`, and `Summary` are all recognized.
- Bullets added through *Fit into experience* go to the top of the chosen job, and then the reorder step can move them.

## Known limits

- Reordering uses a regex over `\begin{itemize}...\end{itemize}`. Nested lists are not handled.
- Keyword matching is literal. "k8s" does not match "Kubernetes" unless the alias is in the catalog.
- Generic words such as `Hiring` and `Monitoring` are in the catalog, so they can appear as gaps. Leave them unticked if they don't describe you.
- The resume layout comes from the pasted `.tex`. The app does not impose a template.
- The PDF is 3 pages with the current sample. Manisha's sample is 4 pages.
- The DOCX keeps the content, order, and dates, but not the PDF's colors, rules, or spacing. Word uses its own styles for those.
- Job labels in the picker are built from the last two lines above each bullet list. A resume with an unusual layout may give unclear labels.

## Security

LaTeX and pandoc can read local files when a `.tex` source points at them. The container limits what they can reach. It runs as a non-root user, its root filesystem is read-only, and it holds no secrets. xelatex runs with `-no-shell-escape`. Keep the port bound to `127.0.0.1` unless you have a reason to expose it.
