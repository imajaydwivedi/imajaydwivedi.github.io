// Resume Tweaker UI. Plain JavaScript, no build step. All server text is inserted with textContent.
(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const els = {
    resumeFile: $("#resume-file"),
    resumeStatus: $("#resume-status"),
    previewResume: $("#preview-resume"),
    jdUrl: $("#jd-url"),
    fetchJd: $("#fetch-jd"),
    jdUrlPanel: $("#jd-url-panel"),
    jdTextPanel: $("#jd-text-panel"),
    jdEditor: $("#jd-editor"),
    jdWords: $("#jd-words"),
    saveJdText: $("#save-jd-text"),
    jdStatus: $("#jd-status"),
    analyze: $("#analyze"),
    analyzeStatus: $("#analyze-status"),
    match: $("#match"),
    matchBefore: $("#match-before"),
    matchAfter: $("#match-after"),
    suggestSection: $("#step-suggest"),
    suggestions: $("#suggestions"),
    covered: $("#covered"),
    coveredGroup: $("#covered-group"),
    reorder: $("#reorder"),
    selectedCount: $("#selected-count"),
    selectAll: $("#select-all"),
    clearAll: $("#clear-all"),
    tweak: $("#tweak"),
    tweakStatus: $("#tweak-status"),
    resultSection: $("#step-result"),
    resultSummary: $("#result-summary"),
    previewTweaked: $("#preview-tweaked"),
  };

  const state = { hasResume: false, hasJd: false };

  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: "same-origin", ...options });
    let body = null;
    try {
      body = await response.json();
    } catch (_) {
      // Non-JSON responses fall through to the generic message below.
    }
    if (!response.ok) {
      const message = body && body.error && body.error.message;
      throw new Error(message || `Request failed (HTTP ${response.status}).`);
    }
    return body;
  }

  function setStatus(element, message, kind = "") {
    element.textContent = message;
    element.className = `status ${kind}`.trim();
  }

  function setBusy(button, busy, idleLabel, busyLabel) {
    button.disabled = busy;
    button.textContent = busy ? busyLabel : idleLabel;
  }

  function refreshButtons() {
    els.previewResume.disabled = !state.hasResume;
    els.analyze.disabled = !(state.hasResume && state.hasJd);
  }

  function resetDownstream() {
    els.match.hidden = true;
    els.suggestSection.hidden = true;
    els.suggestions.replaceChildren();
    els.resultSection.hidden = true;
    setStatus(els.analyzeStatus, "");
  }

  // ---------- Step 1: resume ----------

  els.resumeFile.addEventListener("change", async () => {
    const file = els.resumeFile.files[0];
    if (!file) return;

    const form = new FormData();
    form.append("file", file);
    setStatus(els.resumeStatus, "Uploading and parsing…");
    try {
      const result = await api("/api/resume", { method: "POST", body: form });
      state.hasResume = true;
      resetDownstream();
      const warnings = result.warnings.length ? ` · ${result.warnings.join(" ")}` : "";
      setStatus(
        els.resumeStatus,
        `Loaded “${result.name}” (${result.format.toUpperCase()}, ${result.word_count} words)${warnings}`,
        result.warnings.length ? "warn" : "ok",
      );
    } catch (error) {
      state.hasResume = false;
      setStatus(els.resumeStatus, error.message, "error");
    }
    refreshButtons();
  });

  els.previewResume.addEventListener("click", () => {
    window.open("/api/resume/preview", "_blank", "noopener");
  });

  // ---------- Step 2: job description ----------

  document.querySelectorAll('input[name="jd-mode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      const isUrl = radio.value === "url" && radio.checked;
      els.jdUrlPanel.hidden = !isUrl;
      els.jdTextPanel.hidden = isUrl;
    });
  });

  els.fetchJd.addEventListener("click", async () => {
    const url = els.jdUrl.value.trim();
    if (!url) {
      setStatus(els.jdStatus, "Enter the job posting URL.", "error");
      return;
    }
    setBusy(els.fetchJd, true, "Fetch", "Fetching…");
    setStatus(els.jdStatus, "Fetching the job page…");
    try {
      const result = await api("/api/jd/url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      markJdReady(result.word_count, result.title);
    } catch (error) {
      state.hasJd = false;
      setStatus(
        els.jdStatus,
        `${error.message} If the page blocks automated access, switch to “Paste text” and copy the description in.`,
        "error",
      );
    } finally {
      setBusy(els.fetchJd, false, "Fetch", "Fetching…");
      refreshButtons();
    }
  });

  els.jdEditor.addEventListener("input", updateEditorWordCount);
  els.jdEditor.addEventListener("paste", () => requestAnimationFrame(updateEditorWordCount));

  document.querySelectorAll("[data-cmd]").forEach((button) => {
    button.addEventListener("click", () => {
      els.jdEditor.focus();
      document.execCommand(button.dataset.cmd, false, null);
      updateEditorWordCount();
    });
  });

  els.saveJdText.addEventListener("click", async () => {
    const html = els.jdEditor.innerHTML;
    const text = els.jdEditor.innerText;
    setBusy(els.saveJdText, true, "Use this text", "Saving…");
    try {
      const result = await api("/api/jd/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ html, text }),
      });
      markJdReady(result.word_count, result.title);
    } catch (error) {
      state.hasJd = false;
      setStatus(els.jdStatus, error.message, "error");
    } finally {
      setBusy(els.saveJdText, false, "Use this text", "Saving…");
      refreshButtons();
    }
  });

  function updateEditorWordCount() {
    const words = (els.jdEditor.innerText.match(/\S+/g) || []).length;
    els.jdWords.textContent = `${words} words`;
  }

  function markJdReady(wordCount, title) {
    state.hasJd = true;
    resetDownstream();
    const label = title ? `“${title}”` : "Job description";
    setStatus(els.jdStatus, `${label} is ready · ${wordCount} words`, "ok");
  }

  // ---------- Step 3: analyze ----------

  els.analyze.addEventListener("click", async () => {
    setBusy(els.analyze, true, "Analyze resume against job", "Analyzing…");
    setStatus(els.analyzeStatus, "");
    try {
      const result = await api("/api/analyze", { method: "POST" });
      renderAnalysis(result);
    } catch (error) {
      setStatus(els.analyzeStatus, error.message, "error");
    } finally {
      setBusy(els.analyze, false, "Analyze resume against job", "Analyzing…");
    }
  });

  function renderAnalysis(result) {
    els.matchBefore.textContent = `${Math.round(result.match_before)}%`;
    els.matchAfter.textContent = `${Math.round(result.match_after_estimate)}%`;
    els.match.hidden = false;

    els.suggestions.replaceChildren();
    result.suggestions.forEach((item) => els.suggestions.append(buildSuggestion(item)));
    els.covered.replaceChildren();
    result.covered.forEach((item) => els.covered.append(buildSuggestion(item)));
    els.coveredGroup.hidden = result.covered.length === 0;
    els.suggestSection.hidden = result.suggestions.length === 0 && result.covered.length === 0;
    els.resultSection.hidden = true;

    if (result.suggestions.length === 0) {
      setStatus(els.analyzeStatus, "No missing keywords found. Your resume already covers this job description.", "ok");
    } else {
      setStatus(els.analyzeStatus, `Found ${result.suggestions.length} missing keywords.`, "ok");
    }
    if (!els.suggestSection.hidden) {
      els.suggestSection.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    updateSelection();
  }

  function buildSuggestion(item) {
    const li = document.createElement("li");
    const label = document.createElement("label");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = item.id;
    checkbox.checked = true; // every suggestion starts selected (FR-C1)
    checkbox.name = "suggestion";
    checkbox.addEventListener("change", updateSelection);

    const term = document.createElement("span");
    term.className = "term";
    term.textContent = item.term;

    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = `×${item.count} in job description`;

    const bar = document.createElement("div");
    bar.className = "bar";
    bar.setAttribute("role", "img");
    bar.setAttribute("aria-label", `Relevance ${item.score} of 100`);
    const fill = document.createElement("span");
    fill.style.width = `${item.score}%`;
    bar.append(fill);

    label.append(checkbox, term, meta, bar);
    li.append(label);
    return li;
  }

  // ---------- Step 4: suggestions ----------

  function checkedBoxes() {
    return [...document.querySelectorAll('#step-suggest input[name="suggestion"]')];
  }

  function updateSelection() {
    const boxes = checkedBoxes();
    const selected = boxes.filter((box) => box.checked).length;
    els.selectedCount.textContent = `${selected} of ${boxes.length} keywords selected`;
    const nothingToDo = selected === 0 && !els.reorder.checked;
    els.tweak.disabled = nothingToDo;
    els.tweak.title = nothingToDo ? "Select a keyword, or turn on bullet reordering." : "";
  }

  els.reorder.addEventListener("change", updateSelection);

  els.selectAll.addEventListener("click", () => {
    checkedBoxes().forEach((box) => (box.checked = true));
    updateSelection();
  });

  els.clearAll.addEventListener("click", () => {
    checkedBoxes().forEach((box) => (box.checked = false));
    updateSelection();
  });

  els.tweak.addEventListener("click", async () => {
    const accepted = checkedBoxes()
      .filter((box) => box.checked)
      .map((box) => box.value);
    setBusy(els.tweak, true, "Tweak resume", "Tweaking…");
    setStatus(els.tweakStatus, "");
    try {
      const result = await api("/api/tweak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accepted_ids: accepted, reorder: els.reorder.checked }),
      });
      const listed = result.added.length
        ? `Core Competencies now lists ${result.added.length} keyword${result.added.length === 1 ? "" : "s"}: ${result.added.join(", ")}.`
        : "No keywords were added to Core Competencies.";
      const reordered = result.reordered_sections
        ? ` Reordered bullets in ${result.reordered_sections} section${result.reordered_sections === 1 ? "" : "s"}.`
        : "";
      els.resultSummary.textContent =
        `${listed}${reordered} Match rose from ${Math.round(result.match_before)}% to ${Math.round(result.match_after)}%.`;
      els.resultSection.hidden = false;
      els.resultSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      setStatus(els.tweakStatus, error.message, "error");
    } finally {
      setBusy(els.tweak, false, "Tweak resume", "Tweaking…");
      updateSelection();
    }
  });

  // ---------- Step 5: result ----------

  els.previewTweaked.addEventListener("click", () => {
    window.open("/api/tweaked/preview", "_blank", "noopener");
  });

  refreshButtons();
  updateEditorWordCount();
})();
