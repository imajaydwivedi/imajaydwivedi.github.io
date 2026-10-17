(() => {
  const $ = (id) => document.getElementById(id);
  const state = { tex: "", jobs: [], subsections: [] };

  const els = {
    resume: $("resume"), jd: $("jd"), status: $("status"),
    analysis: $("analysis"), summary: $("summary"), rows: $("addition-rows"),
    covered: $("covered"), gaps: $("gaps"), reorder: $("reorder"),
    result: $("result"), notes: $("notes"), output: $("output"),
    placementBlock: $("placement-block"), placementRows: $("placement-rows"),
    analyzeBtn: $("analyze-btn"), tailorBtn: $("tailor-btn"), tailorStatus: $("tailor-status"),
    downloadTex: $("download-tex"), downloadPdf: $("download-pdf"), downloadDocx: $("download-docx"),
    copy: $("copy-tex"), resumeUrl: $("resume-url"), loadUrlBtn: $("load-url-btn"),
  };

  function setStatus(msg, isError = false) {
    els.status.textContent = msg;
    els.status.classList.toggle("error", isError);
  }

  // Build errors show next to the Build button, so they are visible from there.
  function setTailorStatus(msg, isError = false) {
    els.tailorStatus.textContent = msg;
    els.tailorStatus.classList.toggle("error", isError);
  }

  function busy(btn, on) {
    btn.disabled = on;
  }

  async function post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      throw new Error((await res.text()) || `Request failed (${res.status})`);
    }
    return res;
  }

  function readFileInto(input, target) {
    input.addEventListener("change", async () => {
      const file = input.files[0];
      if (!file) return;
      target.value = await file.text();
      setStatus(`Loaded ${file.name}`);
    });
  }

  function chip(label, extra) {
    const span = document.createElement("span");
    span.className = "chip";
    if (extra) {
      span.appendChild(extra);
    }
    span.appendChild(document.createTextNode(label));
    return span;
  }

  function renderKeywords(covered, gaps) {
    els.covered.replaceChildren();
    if (!covered.length) {
      els.covered.innerHTML = '<span class="empty">None of the job keywords appear in your resume yet.</span>';
    } else {
      covered.forEach((k) => els.covered.appendChild(chip(k)));
    }

    els.gaps.replaceChildren();
    if (!gaps.length) {
      els.gaps.innerHTML = '<span class="empty">No missing keywords from the catalog.</span>';
    } else {
      gaps.forEach((k) => {
        const box = document.createElement("input");
        box.type = "checkbox";
        box.value = k;
        box.addEventListener("change", renderAdditionRows);
        els.gaps.appendChild(chip(k, box));
      });
      // Wrap the label text in the chip so clicks anywhere on the chip toggle it.
      els.gaps.querySelectorAll(".chip").forEach((c) => (c.onclick = (e) => {
        if (e.target.tagName !== "INPUT") c.querySelector("input").click();
      }));
    }
  }

  function renderAdditionRows() {
    const wanted = selectedGaps();
    // Drop rows whose keyword was unticked, keeping what was typed for the rest.
    [...els.rows.querySelectorAll(".addition")].forEach((row) => {
      if (!wanted.includes(row.dataset.keyword)) row.remove();
    });
    wanted.forEach((k) => {
      if (els.rows.querySelector(`.addition[data-keyword="${CSS.escape(k)}"]`)) return;
      els.rows.appendChild(makeRow(k));
    });
    if (!wanted.length) {
      els.rows.innerHTML = '<span class="empty">Tick a missing keyword above to add a bullet for it.</span>';
    } else if (els.rows.querySelector(".empty")) {
      els.rows.querySelector(".empty").remove();
    }
    renderPlacementRows();
  }

  // One picker per ticked keyword: an existing Core Competencies line, or a new labelled line.
  function renderPlacementRows() {
    const wanted = selectedGaps();
    els.placementBlock.classList.toggle("hidden", !(state.subsections.length && wanted.length));
    [...els.placementRows.querySelectorAll(".placement")].forEach((row) => {
      if (!wanted.includes(row.dataset.keyword)) row.remove();
    });
    if (!state.subsections.length) return;
    wanted.forEach((k) => {
      if (els.placementRows.querySelector(`.placement[data-keyword="${CSS.escape(k)}"]`)) return;
      els.placementRows.appendChild(makePlacementRow(k));
    });
  }

  function makePlacementRow(keyword) {
    const row = document.createElement("div");
    row.className = "addition placement";
    row.dataset.keyword = keyword;

    const head = document.createElement("div");
    head.className = "addition-head";
    const title = document.createElement("strong");
    title.textContent = keyword;
    head.append(title);

    const select = document.createElement("select");
    select.className = "placement-line";
    state.subsections.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = String(s.index);
      opt.textContent = `Add to: ${s.label}`;
      select.appendChild(opt);
    });
    const newOpt = document.createElement("option");
    newOpt.value = "new";
    newOpt.textContent = "New line with its own label";
    select.appendChild(newOpt);
    const skipOpt = document.createElement("option");
    skipOpt.value = "skip";
    skipOpt.textContent = "Don't add to core competency";
    select.appendChild(skipOpt);
    select.value = "skip";

    const label = document.createElement("input");
    label.type = "text";
    label.className = "new-label";
    label.maxLength = 60;
    label.value = "Other";
    label.placeholder = "Label for the new line, e.g. Streaming";
    const syncLabel = () => label.classList.toggle("hidden", select.value !== "new");
    select.addEventListener("change", syncLabel);
    syncLabel();

    row.append(head, select, label);
    return row;
  }

  function collectPlacements() {
    return [...els.placementRows.querySelectorAll(".placement")].map((row) => {
      const keyword = row.dataset.keyword;
      const select = row.querySelector("select.placement-line");
      if (select.value === "skip") {
        return { keyword, subsection: null, new_label: null, skip: true };
      }
      if (select.value === "new") {
        const label = row.querySelector("input.new-label").value.trim();
        return { keyword, subsection: null, new_label: label || "Other" };
      }
      return { keyword, subsection: Number(select.value), new_label: null };
    });
  }

  function makeRow(keyword) {
    const row = document.createElement("div");
    row.className = "addition";
    row.dataset.keyword = keyword;

    const head = document.createElement("div");
    head.className = "addition-head";
    const title = document.createElement("strong");
    title.textContent = keyword;
    const count = document.createElement("span");
    count.className = "count";
    count.textContent = "0/300";
    head.append(title, count);

    const select = document.createElement("select");
    state.jobs.forEach((job) => {
      const opt = document.createElement("option");
      opt.value = job.index;
      opt.textContent = job.label;
      select.appendChild(opt);
    });
    select.className = "job";

    const text = document.createElement("textarea");
    text.maxLength = 300;
    text.placeholder = `Your bullet for this job, including "${keyword}"`;
    text.addEventListener("input", () => { count.textContent = `${text.value.length}/300`; });

    row.append(head, select, text);
    return row;
  }

  function collectAdditions() {
    return [...els.rows.querySelectorAll(".addition")]
      .map((row) => ({
        keyword: row.dataset.keyword,
        job_index: Number(row.querySelector("select.job").value),
        bullet: row.querySelector("textarea").value.trim(),
      }))
      .filter((a) => a.bullet && state.jobs.length);
  }

  function selectedGaps() {
    return [...els.gaps.querySelectorAll("input:checked")].map((i) => i.value);
  }

  // No job description: skip the keyword analysis and go straight to the downloads.
  // The resume is returned unchanged.
  function showResumeOnly(tex) {
    state.tex = tex;
    els.output.textContent = tex;
    els.notes.replaceChildren();
    const li = document.createElement("li");
    li.textContent = "No job description given, so the resume is unchanged.";
    els.notes.appendChild(li);
    els.analysis.classList.add("hidden");
    els.result.classList.remove("hidden");
    els.result.scrollIntoView({ behavior: "smooth", block: "start" });
    setStatus("");
  }

  els.analyzeBtn.addEventListener("click", async () => {
    const resume_tex = els.resume.value.trim();
    const jd_text = els.jd.value.trim();
    if (!resume_tex) {
      setStatus("Add a resume first.", true);
      return;
    }
    if (!jd_text) {
      showResumeOnly(els.resume.value);
      return;
    }
    busy(els.analyzeBtn, true);
    setStatus("Analyzing...");
    try {
      const res = await post("/api/analyze", { resume_tex, jd_text });
      const data = await res.json();
      renderKeywords(data.covered, data.gaps);
      const jobsRes = await post("/api/jobs", { resume_tex });
      state.jobs = (await jobsRes.json()).jobs;
      const subsRes = await post("/api/core-subsections", { resume_tex });
      state.subsections = (await subsRes.json()).subsections;
      renderAdditionRows();
      els.summary.textContent =
        `${data.jd_keyword_count} keywords found in the job description. ` +
        `${data.covered.length} already in your resume, ${data.gaps.length} missing.`;
      els.analysis.classList.remove("hidden");
      els.result.classList.add("hidden");
      setStatus("");
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      busy(els.analyzeBtn, false);
    }
  });

  els.tailorBtn.addEventListener("click", async () => {
    busy(els.tailorBtn, true);
    setTailorStatus("Building...");
    try {
      const res = await post("/api/tailor", {
        resume_tex: els.resume.value,
        jd_text: els.jd.value,
        include_keywords: selectedGaps(),
        reorder: els.reorder.checked,
        additions: collectAdditions(),
        placements: collectPlacements(),
      });
      const data = await res.json();
      state.tex = data.tex;
      els.output.textContent = data.tex;

      els.notes.replaceChildren();
      const notes = [];
      notes.push(`Core Competencies: ${data.core_keywords.length} keywords.`);
      notes.push(data.reordered_sections.length
        ? `Reordered bullets in: ${data.reordered_sections.join(", ")}.`
        : "No bullets were reordered.");
      data.warnings.forEach((w) => notes.push({ text: w, warn: true }));
      notes.forEach((n) => {
        const li = document.createElement("li");
        li.textContent = typeof n === "string" ? n : n.text;
        if (n.warn) li.classList.add("warn");
        els.notes.appendChild(li);
      });

      els.result.classList.remove("hidden");
      els.result.scrollIntoView({ behavior: "smooth", block: "start" });
      setTailorStatus("");
    } catch (err) {
      setTailorStatus(err.message, true);
    } finally {
      busy(els.tailorBtn, false);
    }
  });

  function saveBlob(blob, filename) {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }

  els.downloadTex.addEventListener("click", () => {
    saveBlob(new Blob([state.tex], { type: "application/x-tex" }), "resume_tailored.tex");
  });

  async function convertAndSave(btn, url, filename, busyText) {
    busy(btn, true);
    setStatus(busyText);
    try {
      const res = await post(url, { tex: state.tex });
      saveBlob(await res.blob(), filename);
      setStatus("");
    } catch (err) {
      setStatus(err.message, true);
    } finally {
      busy(btn, false);
    }
  }

  els.downloadPdf.addEventListener("click", () =>
    convertAndSave(els.downloadPdf, "/api/pdf", "resume_tailored.pdf", "Compiling PDF (this can take a little while)..."));
  els.downloadDocx.addEventListener("click", () =>
    convertAndSave(els.downloadDocx, "/api/docx", "resume_tailored.docx", "Converting to DOCX..."));

  els.copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(state.tex);
      setStatus("Copied to clipboard.");
    } catch {
      setStatus("Clipboard blocked. Select the text and copy it manually.", true);
    }
  });

  async function loadFromUrl() {
    const urlStatus = $("url-status");
    const url = els.resumeUrl.value.trim();
    if (!url) {
      urlStatus.textContent = "Paste a GitHub or Google Drive link first.";
      urlStatus.classList.add("error");
      return;
    }
    busy(els.loadUrlBtn, true);
    urlStatus.textContent = "Loading resume from link...";
    urlStatus.classList.remove("error");
    try {
      const res = await post("/api/fetch", { url });
      const data = await res.json();
      els.resume.value = data.tex;
      urlStatus.textContent = "Loaded resume from link.";
    } catch (err) {
      urlStatus.textContent = err.message;
      urlStatus.classList.add("error");
    } finally {
      busy(els.loadUrlBtn, false);
    }
  }

  els.loadUrlBtn.addEventListener("click", loadFromUrl);
  els.resumeUrl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") loadFromUrl();
  });

  readFileInto($("resume-file"), els.resume);
  readFileInto($("jd-file"), els.jd);

  fetch("/api/status")
    .then((r) => r.json())
    .then((caps) => {
      els.downloadPdf.classList.toggle("hidden", !caps.pdf);
      els.downloadDocx.classList.toggle("hidden", !caps.docx);
    })
    .catch(() => {});
})();
