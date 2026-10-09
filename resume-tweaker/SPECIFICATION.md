# Resume Tweaker — Specification

**Version:** 0.1 (draft)
**Owner:** Ajay Kumar Dwivedi
**Location:** `resume-tweaker/` inside `imajaydwivedi.github.io`
**Deployment:** Docker container, web service listening on container port **80**, published on host port **8080**

---

## 1. Purpose

Resume Tweaker is a small, self-hosted web application that helps a job seeker align an existing resume with a specific job description (JD).

The user uploads a resume, supplies a JD (as a URL or pasted rich text), and receives a list of keywords and phrases that appear in the JD but are missing from the resume. The user accepts or rejects each suggestion. The app then produces an updated resume that incorporates only the accepted suggestions, which the user can preview and download in PDF, DOCX, or Markdown.

### 1.1 Guiding principles

1. **The user stays in control.** Every suggestion is opt-in. All suggestions are pre-selected, and the user unchecks anything that does not match their real experience. The app never adds a keyword the user has not confirmed.
2. **No invented experience.** The app only adds the exact keywords/phrases the user accepted. It does not write new job bullets, dates, employers, or metrics.
3. **Private by default.** Resumes and JDs are held in memory for a limited time and are never written to a persistent location or sent to a third party.
4. **Runs offline.** Core analysis is deterministic and needs no external AI API. (See §14 for a future LLM-assisted mode.)

---

## 2. Scope

### 2.1 In scope (v1)

- Upload a resume in **PDF, DOC, DOCX, or Markdown** format.
- Preview the uploaded (parsed) resume in a **new browser tab**.
- Provide a JD by **URL** (server fetches and extracts the text) **or** by pasting **rich text** into a text box (formatting preserved for display, plain text used for analysis).
- Submit to **analyze** the resume against the JD.
- Show **keyword/phrase suggestions as checkboxes**, all checked by default.
- Submit **"Tweak Resume"** to apply the checked suggestions to the resume text.
- Preview the **tweaked** resume in a new browser tab, with added terms highlighted.
- **Download** the tweaked resume as PDF, DOCX, or Markdown.
- Run as a single Docker container listening on port 80, mapped to host port 8080.
- Keyword matching from a synonym-aware catalog, with covered and missing keywords shown separately.
- Core Competencies section and optional reordering of Skills and Experience bullets (§16).
- Mobile-first responsive UI, usable from 320 px phones to desktop (§8).

### 2.2 Out of scope (v1)

- User accounts, login, or saved history.
- Multi-resume management or version history.
- Automatic rewriting of bullet points or sentences (only keyword/phrase insertion is supported).
- Scraping JS-rendered job pages (only server-side HTML is fetched).
- Scoring against an ATS product or guaranteeing ATS pass-through.

---

## 3. Users and Primary Flow

**Actor:** A single job seeker running the container locally (or on a private host).

### 3.1 Happy-path flow

```
[1] Upload resume ──► [2] Preview (optional, new tab)
        │
        ▼
[3] Provide JD  (URL  OR  rich-text paste)
        │
        ▼
[4] Click "Analyze"  ──► server parses resume + JD, extracts candidate keywords
        │
        ▼
[5] Suggestions shown as checkboxes (ALL pre-checked)
        │   user unchecks items that don't fit their experience
        ▼
[6] Click "Tweak Resume" ──► server applies checked suggestions to resume text
        │
        ▼
[7] Preview tweaked resume (new tab)  ──► [8] Download PDF / DOCX / Markdown
```

### 3.2 Error flow

Each step shows a clear inline message on failure (unsupported file type, unreadable PDF, unreachable URL, empty JD, no suggestions found). The user can always retry without re-uploading the resume.

---

## 4. Functional Requirements

### 4.1 Resume upload

| ID | Requirement |
|---|---|
| FR-R1 | The page shows a file picker labelled **"Upload your current resume"**. |
| FR-R2 | Accepted extensions: `.pdf`, `.doc`, `.docx`, `.md` (`.markdown` also accepted). |
| FR-R3 | Maximum upload size: **5 MB** (configurable via `MAX_UPLOAD_MB`). |
| FR-R4 | Files are validated by extension **and** magic bytes (PDF `%PDF`, DOCX/ZIP `PK`, DOC OLE `D0 CF 11 E0`). Mismatches are rejected. |
| FR-R5 | The uploaded file is parsed into **normalized Markdown** (the internal canonical format; see §5). |
| FR-R6 | A **Preview** button opens the parsed resume in a **new browser tab** as rendered HTML. |
| FR-R7 | Re-uploading replaces the current resume and clears prior analysis results. |

### 4.2 Job description input

| ID | Requirement |
|---|---|
| FR-J1 | The page offers two input modes, selectable by tabs or radio buttons: **URL** and **Paste text**. |
| FR-J2 | **URL mode:** a text field accepts an `http`/`https` URL. The server fetches it (timeout 10 s, max 2 MB, max 5 redirects) and extracts the readable text. |
| FR-J3 | **Paste mode:** a rich-text box (`contenteditable`) with a minimal toolbar (bold, italic, bullet list, numbered list, clear formatting). Pasted content keeps its basic formatting. |
| FR-J4 | Pasted HTML is **sanitized** on the server (allow-list of tags: `p`, `br`, `strong`, `b`, `em`, `i`, `ul`, `ol`, `li`, `h1`–`h4`, `a`, `span`; all other tags and all attributes except `href` on `a` are stripped). |
| FR-J5 | The JD must contain at least **40 words** after extraction, otherwise the app asks the user to check the input. |

### 4.3 Analysis

| ID | Requirement |
|---|---|
| FR-A1 | Clicking **Analyze** runs the analysis (§6) and returns a list of suggestions. |
| FR-A2 | Each suggestion shows: the keyword/phrase, the number of times it appears in the JD, and a relevance score (0–100). |
| FR-A3 | Suggestions are sorted by relevance, highest first. |
| FR-A4 | Keywords **already present** in the resume (case-insensitive, whole-word match) are **excluded**. |
| FR-A5 | At most **30** suggestions are returned (configurable). |
| FR-A6 | The result also shows a **match score before** (percent of JD keywords already in the resume) and an **estimated score after** tweaking, so the user sees the effect. |

### 4.4 Suggestions as checkboxes

| ID | Requirement |
|---|---|
| FR-C1 | Each suggestion is a checkbox. **All checkboxes are checked by default.** |
| FR-C2 | The user can check/uncheck individually, and there are **Select all** / **Clear all** controls. |
| FR-C3 | The **Tweak Resume** button submits only the checked items. |
| FR-C4 | If no items are checked, the button is disabled, with a tooltip explaining why. |

### 4.5 Tweaking

| ID | Requirement |
|---|---|
| FR-T1 | Clicking **Tweak Resume** applies the checked suggestions to the resume and produces a new version. The original upload is kept so the user can re-tweak with a different selection. |
| FR-T2 | *Superseded in v0.2 (§16): keywords now go to a Core Competencies section.* Former rule: insertion target: a **Skills** section if one exists (heading matching `skill`, `technical skill`, `core competenc`, `competenc`, or `technologies`). If none exists, a new **Keywords** section is created after the Professional Summary (or at the top of the body if no summary exists). |
| FR-T3 | *Superseded in v0.2 (§16).* Former rule: accepted terms are appended in the target section as a comma-separated list, grouped in one line per batch, e.g. `**Additional Keywords:** Kubernetes, Terraform, CI/CD`. |
| FR-T4 | Nothing else in the resume changes. The app must not rewrite, reorder, or delete existing content. |
| FR-T5 | The tweaked resume is shown in a **new browser tab** (preview) with added terms highlighted. |
| FR-T6 | The tweaked preview has the same download options as §4.6. |

### 4.6 Preview and download

| ID | Requirement |
|---|---|
| FR-D1 | Preview endpoints render HTML in a new tab (`target="_blank"`). Both the original and the tweaked resume can be previewed. |
| FR-D2 | Download formats: **PDF**, **DOCX**, **Markdown** (`.md`). |
| FR-D3 | Downloaded filename: `<Name>_Resume_<Company-or-slug>.<ext>`, where `<Name>` comes from the resume's first H1 and `<slug>` from the JD title when detectable (fallback: `tweaked`). Spaces become underscores. |
| FR-D4 | The PDF uses a clean, single-column, ATS-friendly layout (no tables, no images, selectable text). |
| FR-D5 | The DOCX uses real Word heading styles and bullet lists, so it stays editable. |

---

## 5. Internal Document Model

All formats convert to and from **one canonical form: Markdown** (CommonMark with GFM tables).

| Input | Parsing approach |
|---|---|
| `.md` | Read as UTF-8 text. Used as-is after normalizing line endings. |
| `.docx` | `python-docx`. Headings map to `#`/`##`/`###` by style name. Paragraphs with list styles map to `- `. Bold/italic runs map to `**`/`*`. Tables are flattened to Markdown tables. |
| `.doc` | Converted to `.docx` with LibreOffice (`soffice --headless --convert-to docx`), then parsed as DOCX. |
| `.pdf` | `pdfplumber` text extraction, page by page, with lines grouped by y-position. Headings are inferred from font size where available. Output is a best-effort Markdown; the preview shows a warning that PDF structure may be approximate. |

**Output conversions from Markdown:**

- **Preview HTML:** `markdown-it-py` (with tables enabled), wrapped in a print-friendly stylesheet.
- **PDF:** Markdown → HTML → `WeasyPrint`.
- **DOCX:** Markdown tokens → `python-docx` (headings, bullets, bold/italic, tables).
- **MD:** Markdown text as-is.

**Limits:** documents over 5 MB, over 2000 lines, or containing embedded images are rejected or have images dropped with a warning shown to the user.

---

## 6. Analysis Algorithm

Deterministic and offline. Two keyword sources feed the result: a curated **catalog** (precise, synonym-aware) and **phrase candidates** mined from the JD (broad, catches what the catalog lacks).

**Part A — Catalog (`app/catalog.py`, `app/data/keyword_groups.json`)**

1. Each catalog entry is a *group*: a canonical label plus synonyms (`Go` = `Golang`, `Kubernetes` = `K8s`). A group is found when any alias appears as a whole word.
2. Case-sensitive matching applies to `Go`, `R`, and any all-caps alias of five characters or fewer (`DR`, `ETL`, `IAM`). This stops prose such as "go live" or "Dr. Smith" from matching.
3. If one matched label contains another (`Site Reliability Engineering` and `Reliability Engineering`), only the longer label is kept.
4. Each JD group is classified: **covered** if the resume already contains any alias, otherwise **missing**.

**Part B — Phrase candidates**

1. **Normalize** both texts: lower-case, unify dashes and quotes, strip URLs and emails. Hyphenated words are split (`terraform-managed` → `terraform managed`) unless the hyphenated form is a dictionary term (`scikit-learn`).
2. **Tokenize** each line into clauses (split on commas, semicolons, colons, and sentence ends, so phrases never cross them). Generate **n-grams** of length 1–3. Discard grams that start or end with a stopword, contain an inner stopword, are entirely generic, or contain no letters (`5+ years`).
3. **Score** each candidate:
   - *Frequency:* `1 + log(count)`.
   - *Technical bonus:* ×1.4 if the term is in `data/tech_terms.txt`.
   - *Position bonus:* ×1.2 if the term appears in the JD's first 25% of lines, or under a requirements heading (`requirements`, `responsibilities`, `qualifications`, `skills`, …). A section ends at a line that starts with `About us`, `Benefits`, `Compensation` and similar.
   - *Non-technical penalty:* a single non-technical word ×0.6 (`build`, `code`). A multi-word phrase containing a generic word ×0.3.
   - A candidate that occurs once and is neither technical nor in a requirements section is dropped.
4. **Drop** phrases that overlap a catalog keyword (so `kubernetes clusters` does not duplicate `Kubernetes`), and phrases that overlap a higher-scored candidate.

**Part C — Results**

1. **`suggestions` (missing):** catalog groups not in the resume, plus phrase candidates not in the resume, de-duplicated and sorted by score. Capped at `MAX_SUGGESTIONS`.
2. **`covered`:** catalog groups already in the resume. Listed separately so they can go into Core Competencies without adding anything new.
3. **Scores** are normalized to 0–100 across both lists.
4. **Match score (before):** `covered JD keywords / JD keywords`, where JD keywords are the catalog groups in the JD plus the top 40 phrase candidates.
5. **Match score (after):** the same ratio, counting accepted missing keywords as covered.

**Known limitation:** phrase candidates can still be generic or partial (for example, `server high`). The checkbox step exists so the user can reject these before anything is written.
## 7. HTTP API

Base path: `/api`. All responses are JSON unless noted. Sessions are tracked with an HTTP-only cookie `rt_session` (random 128-bit id).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Serves the web UI (HTML). |
| `GET` | `/healthz` | Liveness probe. Returns `{"status":"ok"}`. |
| `POST` | `/api/resume` | Multipart upload, field `file`. Returns `{name, format, word_count, warnings[]}`. |
| `GET` | `/api/resume/preview` | Original parsed resume as HTML (new tab). |
| `POST` | `/api/jd/url` | Body `{ "url": "..." }`. Returns `{ "text_preview", "word_count" }`. |
| `POST` | `/api/jd/text` | Body `{ "html": "...", "text": "..." }`. Returns `{ "word_count" }`. |
| `POST` | `/api/analyze` | Runs analysis on the stored resume and JD. Returns `{ match_before, match_after_estimate, suggestions: [{id, term, count, score, source}], covered: [{id, term, count, score, source}] }`. `suggestions` are missing keywords; `covered` are already in the resume. `source` is `catalog` or `phrase`. |
| `POST` | `/api/tweak` | Body `{ "accepted_ids": [...], "reorder": true }`. `accepted_ids` may reference items from `suggestions` or `covered`. Creates the tweaked version. Returns `{ added, reordered_sections, match_before, match_after }`. |
| `GET` | `/api/tweaked/preview` | Tweaked resume as HTML (new tab). 404 if no tweak exists. |
| `GET` | `/api/download/{which}/{fmt}` | `which` ∈ `original`, `tweaked`; `fmt` ∈ `pdf`, `docx`, `md`. Returns the file with `Content-Disposition: attachment`. |

**Error format:** `{ "error": { "code": "UNSUPPORTED_FORMAT", "message": "..." } }`. Statuses in use: 404 (nothing to show or download), 409 (step out of order, such as analyze before upload), 413 (upload or page too large), 415 (unsupported or mismatched file type), 422 (invalid input, such as a short JD or no selection), 502 (job page could not be fetched), 503 (`.doc` support not in this build).

**Tweak rules:** the request is rejected with `NO_SELECTION` only when no keyword is selected and `reorder` is `false`.

**Session state** (in memory only): original resume Markdown, JD text, suggestions, tweaked Markdown. Sessions expire after **60 minutes of inactivity**. Memory is capped at **50 concurrent sessions**; the oldest is evicted first.

---

## 8. User Interface

Single page, mobile-first. The base styles are for phones, and wider layouts are added with `min-width` queries. Light and dark colour schemes follow `prefers-color-scheme`.

**Layout (top to bottom on phones):**

1. **Header:** "Resume Tweaker" and a one-line description.
2. **Step 1 — Resume:** file input (PDF, DOC, DOCX, Markdown), **Preview resume** button (new tab, disabled until upload).
3. **Step 2 — Job description:** segmented control `Job page URL | Paste text`.
   - URL: text field and **Fetch**.
   - Paste: rich-text box with toolbar (bold, italic, lists, clear) and word count, then **Use this text**.
4. **Step 3 — Analyze:** **Analyze resume against job** button, then two score tiles: **Match today** and **Match if all kept**.
5. **Step 4 — Suggested keywords:**
   - Summary line ("X of Y keywords selected") and **Select all** / **Clear all**.
   - **Missing from your resume:** checkbox list, each with the term, its count in the JD, and a relevance bar. All pre-checked.
   - **Already in your resume:** checkbox list of covered keywords. All pre-checked. Checked items are listed under Core Competencies.
   - **Reorder** checkbox: "Reorder Skills and Experience bullets so the job-relevant ones come first. Wording is not changed." Pre-checked.
   - **Tweak resume** button. Disabled when nothing is checked and reordering is off.
6. **Step 5 — Tweaked resume:** a summary of what changed, **Preview tweaked resume** (new tab), download buttons for **PDF**, **DOCX**, **Markdown** (tweaked), and the same three for the original.

**Responsive behaviour:**

| Width | Layout |
|---|---|
| Under 380 px | Single column. Tool buttons shrink to fit. |
| 380–519 px | Single column. The job URL field and Fetch button each take a full row. |
| 520–599 px | Single column. Standard spacing. |
| 600 px and up | Match tiles side by side. Downloads in a row of three. Keyword rows show the count on the right. |
| 900 px and up | Once results exist, Analyze and the keyword lists sit side by side so both are visible at once. |

**Touch devices** (`pointer: coarse`): targets are at least 44–48 px. Checkboxes are 26 px.

**Other requirements:**

- Inputs use 16 px text, so iOS does not zoom on focus.
- Safe-area insets are respected on notched phones.
- Motion is disabled when the user prefers reduced motion.
- No horizontal page scroll at any width. Wide tables in the resume preview scroll inside their own box.

**Accessibility:** all controls are labelled; checkboxes are keyboard operable; status messages use `aria-live="polite"`; focus rings are visible; contrast meets WCAG AA.

## 9. Non-Functional Requirements

| Area | Requirement |
|---|---|
| **Privacy** | No persistent storage of resumes or JDs. No telemetry. No third-party API calls in v1. |
| **Security** | Input sanitized (§FR-J4). URL fetch blocks private, loopback, and link-local addresses (SSRF protection) and only allows `http`/`https`. Uploads are checked for size and type. Response headers: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`. The UI page uses a CSP that allows only same-origin scripts and styles. Resume previews use a stricter CSP (`default-src 'none'`), and raw HTML in uploaded Markdown is escaped. **No authentication in v1:** anyone who can reach the published port can use the app. |
| **Responsiveness** | Usable from 320 px phones to desktop widths, with touch-sized targets on touch devices (§8). |
| **Performance** | Analysis of a 2-page resume and a 1,000-word JD completes in under 1 s on a 1-vCPU container. PDF export under 3 s. |
| **Reliability** | Healthcheck endpoint. Graceful error for every failure path. No crash on malformed input (fuzzed in tests). |
| **Portability** | Intended for `linux/amd64` and `linux/arm64`. Verified so far on `linux/amd64` only. |
| **Observability** | Structured logs to stdout (level via `LOG_LEVEL`). Logs never contain resume or JD contents. |
| **Configuration** | Environment variables: `PORT` (default `80`, the port inside the container), `MAX_UPLOAD_MB` (5), `SESSION_TTL_MIN` (60), `MAX_SUGGESTIONS` (30), `LOG_LEVEL` (`INFO`). |

---

## 10. Docker Packaging

### 10.1 Image

- **Base:** `python:3.12-slim-bookworm`.
- **System packages:** WeasyPrint runtime libraries (`libpango-1.0-0`, `libpangoft2-1.0-0`, `libharfbuzz0b`, `libharfbuzz-subset0`, `fonts-dejavu-core`), `libcap2-bin` (for `setcap`), and `libreoffice-writer-nogui` for `.doc` conversion (installed with `--no-install-recommends`).
- **User:** non-root user `app` (UID 10001).
- **Port:** the server listens on `0.0.0.0:80` inside the container. Port 80 is privileged, so the image grants only `cap_net_bind_service` to the Python binary (`setcap`) and keeps the `app` user unprivileged. This grant only works if the container does not set `no-new-privileges`, so `docker-compose.yml` does not set it.
- **Healthcheck:** `http://127.0.0.1:80/healthz` every 30 s.
- **Server:** `uvicorn` with a single worker (sessions are in memory, so multiple workers are not supported in v1).

### 10.2 Run

```bash
docker build -t resume-tweaker:latest resume-tweaker/
docker run --rm -p 8080:80 resume-tweaker:latest
# then open http://localhost:8080
```

The app listens on port 80 inside the container, and `-p 8080:80` publishes it on host port 8080. `-p 8080:80` binds to all network interfaces, so other devices on the same network can reach it. To keep it on this machine only, use `-p 127.0.0.1:8080:80`.

`docker-compose.yml` provides the same with `docker compose up --build`, mapping `8080:80`.

### 10.3 Image size

Target: under **1.2 GB** (LibreOffice is the largest contributor). An alternative `slim` build without `.doc` support (`--build-arg WITH_DOC=0`) is supported, for a smaller image.

---

## 11. Project Structure

```
resume-tweaker/
├── SPECIFICATION.md          ← this document
├── README.md                 ← how to build, run, and use
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt          ← pinned; pydyf==0.10.0 is required by WeasyPrint 62.x
├── requirements-dev.txt
├── app/
│   ├── __init__.py
│   ├── main.py               ← FastAPI app, routes, session handling
│   ├── config.py             ← env-var settings
│   ├── sessions.py           ← in-memory session store with TTL
│   ├── parsers/
│   │   ├── __init__.py       ← format detection + dispatch
│   │   ├── markdown_parser.py
│   │   ├── docx_parser.py
│   │   ├── doc_parser.py     ← LibreOffice conversion, then docx_parser
│   │   └── pdf_parser.py
│   ├── errors.py             ← ServiceError (status, code, message)
│   ├── jd.py                 ← URL fetch (SSRF-safe) and HTML sanitizing
│   ├── catalog.py            ← synonym-aware keyword catalog matcher (§6 Part A)
│   ├── analyzer.py           ← catalog + phrase analysis, covered/missing split (§6)
│   ├── tweaker.py            ← Core Competencies insertion and bullet reordering (§4.5)
│   ├── render/
│   │   ├── html.py           ← Markdown → HTML preview
│   │   ├── resume.css        ← shared print/preview stylesheet
│   │   ├── preview.css       ← screen-only extras (dark mode)
│   │   ├── pdf.py            ← Markdown → PDF (WeasyPrint)
│   │   └── docx.py           ← Markdown → DOCX
│   ├── data/keyword_groups.json ← keyword catalog with synonym groups (adapted from Manisha's tailor)
│   ├── data/tech_terms.txt   ← curated technology dictionary
│   ├── data/stopwords.txt
│   ├── data/generic_terms.txt
│   └── static/
│       ├── index.html
│       ├── app.js
│       └── style.css
└── tests/
    ├── fixtures/             ← sample resume and JD files
    ├── test_parsers.py
    ├── test_analyzer.py
    ├── test_catalog.py
    ├── test_tweaker.py
    ├── test_jd.py
    └── test_api.py
```

---

## 12. Testing and Acceptance Criteria

### 12.1 Automated tests

- **Parsers:** each format yields Markdown containing the resume's name and at least one bullet. Corrupt files return `UNSUPPORTED_FORMAT` or `PARSE_ERROR`, not a 500.
- **Analyzer:** every suggestion is absent from the resume. Known JD terms (e.g. `terraform`) are returned. Catalog keywords in the resume appear under `covered`, not `suggestions`. Stopword-only phrases are never returned.
- **Catalog:** synonyms match each other (`Golang` ↔ `Go`, `K8s` ↔ `Kubernetes`). Case-sensitive aliases (`Go`, `DR`) do not match ordinary prose. Whole-word matching only.
- **Tweaker:** with nothing selected and reordering off, the output equals the input byte-for-byte. Accepted keywords go into Core Competencies once each, four per line. Unaccepted terms never appear. Reordering only moves whole bullets within Skills and Experience sections, never across job headings, and the multiset of lines is unchanged (diff check).
- **Sanitizer:** `<script>`, `onerror=`, and `javascript:` URLs are removed.
- **SSRF:** `http://127.0.0.1`, `http://169.254.169.254`, and `file:///` are rejected.
- **API:** end-to-end upload → analyze → tweak → download in each format.

### 12.2 Acceptance checklist (manual)

- [ ] `docker build` and `docker run -p 8080:80` start without errors.
- [ ] `http://localhost:8080` loads the UI (host 8080 to container 80).
- [ ] Upload of each of `.pdf`, `.doc`, `.docx`, `.md` parses and shows the name and word count.
- [ ] **Preview** opens the resume in a new tab.
- [ ] URL mode fetches a public JD page and produces a word count.
- [ ] Paste mode keeps bold and bullets visible in the editor.
- [ ] Analyze returns suggestions, all checked by default.
- [ ] Unchecking an item and clicking **Tweak Resume** leaves that term out of the output.
- [ ] The tweaked preview opens in a new tab and shows highlighted additions.
- [ ] PDF, DOCX, and Markdown downloads open correctly.
- [ ] Layout works at 320 px, 390 px, and 1366 px widths without horizontal scrolling.
- [ ] On a touch device, all buttons and checkboxes are easy to tap.
- [ ] Reorder checkbox moves job-relevant bullets up; the bullet text is unchanged.
- [ ] Core Competencies appears after the summary in the tweaked resume and in all three downloads.

---

## 13. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| PDF text extraction loses structure (columns, icons) | Warning shown to the user. The original format remains available for download. Future: OCR-free layout heuristics. |
| Analyzer proposes irrelevant phrases | All suggestions pre-checked but reviewable; term list is editable (`tech_terms.txt`). |
| JD sites block scraping or require JavaScript | Paste mode is the fallback. The error message points to it. |
| Image size from LibreOffice | `WITH_DOC=0` build option. |
| Dependence on a single in-memory worker | Documented; acceptable for single-user local use. |
| Published port reachable from the network, with no login | Run with `-p 127.0.0.1:8080:80` to keep it on this machine. Add authentication before any shared deployment. |
| Port 80 needs `cap_net_bind_service` | Granted by `setcap` in the image. Adding `no-new-privileges` to the container would break this, so compose does not set it. |
| Catalog and phrase matches can be wrong or generic | Every suggestion is shown with its source and can be unchecked before anything is written. Extend `keyword_groups.json` and `tech_terms.txt` as needed. |

---

## 14. Future Enhancements (not in v1)

1. **LLM-assisted suggestions** (optional, behind an env var such as `ANTHROPIC_API_KEY`): better phrasing and context-aware suggestions. This is opt-in because it sends resume content to an external API.
2. **Rewrite-in-place suggestions** for bullet points, still shown as checkboxes with before/after diffs.
3. **Side-by-side diff view** of original and tweaked resumes.
4. **Multiple JD profiles** per resume.
5. **Optional persistent volume** (`/data`) to keep sessions across restarts.

---

## 15. Open Questions

1. Should the app also accept `.rtf` or `.txt` resumes? (Not included in v1.)
2. ~~Should the default keywords section name be configurable?~~ Resolved in v0.2: keywords go to a fixed **Core Competencies** section (§16).
3. Is a single-user, local-only deployment sufficient, or should basic authentication be added before any public deployment? (Assumed: local use only in v1.)

---

## 16. Revision 0.2 — adopted from Manisha's rule-based tailor

Source: `help-from-manisha.txt`. Its LaTeX implementation was not copied. Its ideas were ported to Markdown, and its 178-entry keyword catalog was converted into `app/data/keyword_groups.json`.

### 16.1 What changed

| Area | v0.1 | v0.2 |
|---|---|---|
| Keyword matching | Frequency-based n-grams only | Synonym-aware catalog (`Golang` = `Go`, `K8s` = `Kubernetes`) first, then n-gram phrases for anything the catalog lacks |
| Ambiguous aliases | — | `Go`, `R`, and short all-caps acronyms (`DR`, `ETL`) match case-sensitively and as whole words |
| Gap vs. covered | Only gaps were suggested | **Missing** keywords are suggested. Keywords **already in the resume** are listed separately as *Already in your resume* |
| Where keywords go (FR-T2, FR-T3) | Appended to Skills as `**Additional Keywords:**` | Listed in a **Core Competencies** section after the summary, four per line (`- A \| B \| C \| D`). An existing Core Competencies section is extended |
| Bullet ordering (new) | — | Optional. Bullets in Skills and Experience sections are stably sorted by how many JD keywords they contain. Wording, job order, and headings are never changed |
| Opt-in (FR-C1, FR-C3) | Gap suggestions only | Both groups are pre-checked. Unchecking a covered keyword leaves it out of Core Competencies |

FR-T2 and FR-T3 are superseded by the Core Competencies behavior above. FR-T1, FR-T4, FR-T5, and FR-T6 still apply.

### 16.2 Matching rules

1. Catalog groups are matched whole-word and case-insensitively, except for case-sensitive aliases (see above).
2. If one matched label contains another (for example, "Site Reliability Engineering" and "Reliability Engineering"), only the longer one is kept.
3. Phrase candidates are dropped if they overlap a catalog keyword, so "kubernetes clusters" does not duplicate "Kubernetes".

### 16.3 API changes

- `POST /api/analyze` returns `suggestions` (missing) and `covered` (already present). Each item has `source` set to `catalog` or `phrase`.
- `POST /api/tweak` accepts `{"accepted_ids": [...], "reorder": true}`. `accepted_ids` may reference items from either list. The response adds `reordered_sections`.
- A tweak with no selection is rejected only when `reorder` is also false.

### 16.4 Principle

The truthfulness rule from §1.1 still holds, and Core Competencies is built from keywords the resume already supports or the user explicitly kept. Nothing is inferred beyond that.
