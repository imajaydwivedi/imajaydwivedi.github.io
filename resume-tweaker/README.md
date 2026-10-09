# Resume Tweaker

Align your resume with a job description. Upload your resume, give the job description (a URL or pasted text), review the keyword suggestions, and download a tweaked resume in PDF, DOCX, or Markdown. You decide every change: suggestions start checked, and only the ones you keep are added.

See [SPECIFICATION.md](SPECIFICATION.md) for the full requirements.

## Quick start

```bash
cd resume-tweaker
docker build -t resume-tweaker:latest .
docker run --rm -p 8080:80 resume-tweaker:latest
```

Then open <http://localhost:8080>. The app listens on port 80 inside the container; `-p 8080:80` maps it to port 8080 on your machine.

Or with Compose:

```bash
docker compose up --build
```

### Smaller image (no `.doc` support)

LibreOffice is the largest dependency. To skip it, build without `.doc` support. `.pdf`, `.docx`, and `.md` still work.

```bash
docker build --build-arg WITH_DOC=0 -t resume-tweaker:slim .
```

## Using it

1. **Upload** your resume (PDF, DOC, DOCX, or Markdown, max 5 MB). Click **Preview resume** to open it in a new tab.
2. **Provide the job description** either by pasting a job page URL, or by pasting text into the rich-text box. If a site blocks automated fetching, use the paste box.
3. **Analyze.** The app shows your current match and the match you would get if you kept all suggestions.
4. **Review the suggestions.** All are checked. Uncheck any that do not match your real experience.
5. **Tweak resume.** The kept keywords are added to your Skills section (or a new *Additional Keywords* section). Nothing else changes.
6. **Preview and download** the tweaked resume as PDF, DOCX, or Markdown.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `80` | Port the server listens on inside the container. Map it to any host port with `-p <host>:<PORT>`. |
| `MAX_UPLOAD_MB` | `5` | Largest accepted resume upload. |
| `SESSION_TTL_MIN` | `60` | Idle time before a session's data is discarded. |
| `MAX_SUGGESTIONS` | `30` | Most suggestions returned per analysis. |
| `LOG_LEVEL` | `INFO` | Python log level. Logs never include resume or job description text. |

## Privacy

- Resumes and job descriptions are held **in memory only**, keyed by an HTTP-only session cookie, and are discarded after the idle timeout or a container restart.
- Nothing is sent to third-party services. Analysis is deterministic and runs locally.
- Only the server fetches job URLs, and it refuses private, loopback, and link-local addresses.

## Limitations

- **Keyword suggestions are heuristic.** They come from term frequency, a technology dictionary (`app/data/tech_terms.txt`), and position in the posting. Review them before keeping them. Extend the dictionary for your domain.
- **PDF input is approximate.** Column layouts, icons, and text boxes can scramble the order of text. The preview shows a warning. For best results, upload DOCX or Markdown.
- **Scanned PDFs are not supported** (no OCR).
- **Single worker.** Sessions live in process memory, so run one container per user. Do not put it behind a load balancer that spreads one user across instances.
- **URL fetch is not JavaScript-aware.** Pages that build their content in the browser need the paste option.
- The URL check resolves the hostname before fetching. A DNS-rebinding attack could still race that check. Run the container on a trusted network if this matters to you.

## Development

Run the tests inside the image, with the source mounted:

```bash
docker run --rm --user root -v "$PWD":/opt/resume-tweaker -w /opt/resume-tweaker \
  --entrypoint sh resume-tweaker:latest \
  -c "pip install -q -r requirements-dev.txt && python -m pytest -q -p no:cacheprovider tests"
```

Layout:

```
app/
  main.py           routes (FastAPI)
  analyzer.py       keyword extraction and scoring
  tweaker.py        inserts accepted keywords into the Markdown
  jd.py             job description fetch (SSRF-guarded) and sanitizing
  parsers/          PDF, DOC, DOCX, Markdown to Markdown
  render/           Markdown to HTML preview, PDF, DOCX
  sessions.py       in-memory session store
  data/             technology dictionary, stopwords, generic terms
  static/           single-page UI
tests/              pytest suite and fixtures
```
