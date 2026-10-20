from app.tailor import analyze, build_core_competencies, latex_escape, strip_latex, tailor
from app.tailor import extract_jd_keywords

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

RESUME = (FIXTURES / "sample_resume.tex").read_text()
JD = (FIXTURES / "sample_jd.txt").read_text()


def test_latex_escape_special_chars():
    assert latex_escape("R&D 50% $5 #1 a_b") == r"R\&D 50\% \$5 \#1 a\_b"


def test_strip_latex_keeps_escaped_percent_and_drops_comments():
    text = "Cut 15\\% costs % this is a comment\n\\textbf{Kubernetes}"
    plain = strip_latex(text)
    assert "15\\%" in plain
    assert "this is a comment" not in plain
    assert "Kubernetes" in plain


def test_synonym_groups_match():
    jd = "Strong Golang and K8s experience"
    assert "Go" in extract_jd_keywords(jd)
    assert "Kubernetes" in extract_jd_keywords(jd)


def test_case_sensitive_aliases_ignore_prose():
    # "Go" should not match the English word "go", and "DR" should not match "dr."
    assert "Go" not in extract_jd_keywords("Let us go live next week")
    assert "Disaster Recovery" not in extract_jd_keywords("Dr. Patel will interview you")
    assert "Disaster Recovery" in extract_jd_keywords("Owned DR runbooks")


def test_analyze_splits_covered_and_gaps():
    covered, gaps = analyze(RESUME, JD)
    assert "Terraform" in covered
    assert "Prometheus" in covered
    assert "PostgreSQL" in covered
    assert "Kubernetes" in gaps
    assert "Kafka" in gaps
    assert not set(covered) & set(gaps)


def test_no_gap_is_added_without_confirmation():
    result = tailor(RESUME, JD)
    assert "Kafka" not in result.core_keywords
    assert "Kafka" not in result.tex


def test_confirmed_gap_is_added_and_non_gap_is_ignored():
    result = tailor(RESUME, JD, include_keywords=["Kafka", "Oracle NetSuite-not-in-jd"])
    assert "Kafka" in result.core_keywords
    assert "Oracle NetSuite-not-in-jd" not in result.core_keywords
    assert "\\section{Core Competencies}" in result.tex


def test_core_competencies_inserted_after_summary():
    result = tailor(RESUME, JD)
    summary_at = result.tex.index("\\section{Summary}")
    core_at = result.tex.index("\\section{Core Competencies}")
    skills_at = result.tex.index("\\section{Skills}")
    assert summary_at < core_at < skills_at


def test_tailor_never_removes_or_changes_existing_wording():
    result = tailor(RESUME, JD, include_keywords=["Kafka"])
    for line in RESUME.splitlines():
        if line.strip().startswith("\\item"):
            assert line.strip() in result.tex


def test_reorder_moves_relevant_bullets_first():
    result = tailor(RESUME, JD)
    assert "experience" in result.reordered_sections or "skills" in result.reordered_sections
    exp = result.tex[result.tex.index("\\section{Experience}"):]
    # The bullet mentioning incident response and postmortems has more JD hits than patching.
    assert exp.index("Led on-call rotation") < exp.index("Ran monthly patching")


def test_reorder_can_be_turned_off():
    result = tailor(RESUME, JD, reorder=False)
    assert result.reordered_sections == []
    assert result.tex.index("Ran monthly patching") < result.tex.index("Led on-call rotation")


def test_existing_core_competencies_section_is_not_duplicated():
    resume = RESUME.replace("\\section{Education}", "\\section{Core Competencies}\n\\begin{itemize}\\item X\\end{itemize}\n\\section{Education}")
    result = tailor(resume, JD, include_keywords=["Kafka"])
    assert result.tex.count("\\section{Core Competencies}") == 1
    assert any("already has a Core Competencies" in w for w in result.warnings)


def test_no_sections_returns_unchanged_with_warning():
    result = tailor("plain text, no headings", JD)
    assert result.tex == "plain text, no headings"
    assert result.warnings


def test_core_block_escapes_latex_chars():
    block = build_core_competencies(["C++", "R&D"])
    assert "R\\&D" in block


def test_professional_summary_heading_is_recognized():
    resume = RESUME.replace("\\section{Summary}", "\\section{Professional Summary}")
    result = tailor(resume, JD)
    assert result.tex.index("\\section{Professional Summary}") < result.tex.index("\\section{Core Competencies}") < result.tex.index("\\section{Skills}")


AJAY = (Path(__file__).parents[1] / "samples" / "ajay_resume.tex").read_text()


def test_experience_jobs_lists_each_job():
    from app.tailor import experience_jobs

    jobs = experience_jobs(AJAY)
    assert [j["index"] for j in jobs] == list(range(len(jobs)))
    assert "Tessell" in jobs[0]["label"]
    assert "AngelOne" in jobs[1]["label"]


def test_bullet_is_added_to_chosen_job_and_escaped():
    from app.tailor import add_bullets

    out = add_bullets(AJAY, [{"keyword": "Kafka", "job_index": 1, "bullet": "Ran Kafka consumers & 50% retries"}])
    assert "\\item Ran Kafka consumers \\& 50\\% retries" in out
    assert out.count("Ran Kafka consumers") == 1
    # It goes at the top of job 1 (AngelOne), before its first existing bullet, and job 0 is unchanged.
    assert out.index("Ran Kafka consumers") < out.index("Built a DB AI agent")
    assert out.index("Ran Kafka consumers") > out.index("Tessell")


def test_bullet_must_contain_its_keyword():
    import pytest
    from app.tailor import AdditionError, add_bullets

    with pytest.raises(AdditionError):
        add_bullets(RESUME, [{"keyword": "Kafka", "job_index": 0, "bullet": "Ran patching jobs"}])


def test_unknown_job_index_is_rejected():
    import pytest
    from app.tailor import AdditionError, add_bullets

    with pytest.raises(AdditionError):
        add_bullets(RESUME, [{"keyword": "Kafka", "job_index": 9, "bullet": "Kafka pipelines"}])


def test_tailor_with_addition_confirms_keyword_and_places_bullet():
    result = tailor(RESUME, JD, additions=[{"keyword": "Kafka", "job_index": 0, "bullet": "Built Kafka pipelines for alerts"}])
    assert "Kafka" in result.core_keywords
    assert "\\item Built Kafka pipelines for alerts" in result.tex


def test_enterprise_jd_terms_are_flagged_as_gaps():
    # Terms from a systems-reliability JD that the catalog used to miss.
    jd = "Strong VMware ESXi, Citrix, Enterprise Storage and Layer 2/3 networking skills; mentor juniors"
    jd_keywords = extract_jd_keywords(jd)
    for label in ["VMware", "ESXi", "Citrix", "Enterprise Storage", "Layer 2/3 Networking", "Mentoring"]:
        assert label in jd_keywords
    _, gaps = analyze("\\section{Skills}\nLinux, Python", jd)
    assert "ESXi" in gaps and "Citrix" in gaps and "Enterprise Storage" in gaps


def test_short_storage_acronyms_ignore_prose():
    # "san" and "nas" in ordinary words must not count as SAN/NAS storage.
    assert "Enterprise Storage" not in extract_jd_keywords("Visit San Diego for the nascent project")
    assert "Enterprise Storage" in extract_jd_keywords("Managed SAN and NAS arrays")


def test_confirmed_gap_keywords_reach_existing_core_competencies():
    # Regression: ticked gap keywords were dropped when Core Competencies already existed.
    resume = (
        "\\section{Core Competencies}\n\\begin{itemize}\n  \\item Linux\n\\end{itemize}\n"
        "\\section{Experience}\n\\begin{itemize}\n  \\item Ran jobs\n\\end{itemize}\n"
    )
    jd = "Looking for Kafka and VMware experience"
    result = tailor(resume, jd, include_keywords=["Kafka", "VMware"])
    core = result.tex[result.tex.index("\\section{Core Competencies}"):result.tex.index("\\section{Experience}")]
    assert "Kafka" in core and "VMware" in core
    assert result.tex.count("\\section{Core Competencies}") == 1
    assert "Linux" in core


SAMPLE = (Path(__file__).parent.parent / "samples" / "dbre.tex").read_text()


def _core_text(tex):
    start = tex.index("\\section{Core Competencies}")
    return tex[start : tex.index("\\section{", start + 5)]


def test_core_subsections_lists_existing_lines():
    from app.tailor import core_subsections
    labels = [s["label"] for s in core_subsections(SAMPLE)]
    assert "Cloud and Containers" in labels
    assert "Automation and Scripting" in labels


def test_keyword_placed_into_chosen_existing_line():
    # Self-contained: does not depend on the sample resume's current wording.
    resume = (
        "\\section{Core Competencies}\n\\begin{itemize}\n"
        "  \\item \\textbf{Cloud \\& Containers:} AWS, Azure, Kubernetes\n"
        "  \\item \\textbf{Monitoring:} Prometheus\n\\end{itemize}\n"
        "\\section{Experience}\n\\begin{itemize}\n  \\item Ran jobs\n\\end{itemize}\n"
    )
    from app.tailor import core_subsections
    idx = next(s["index"] for s in core_subsections(resume) if s["label"] == "Cloud & Containers")
    result = tailor(resume, "Looking for Microservices experience", include_keywords=["Microservices"],
                    placements=[{"keyword": "Microservices", "subsection": idx}])
    assert result.gaps == ["Microservices"] or "Microservices" in result.core_keywords
    cloud_line = next(l for l in _core_text(result.tex).splitlines() if "Cloud \\& Containers" in l)
    cloud_line = next(l for l in _core_text(result.tex).splitlines() if "Cloud \\& Containers" in l)
    assert cloud_line.rstrip().endswith("Microservices")
    assert _core_text(result.tex).count("Microservices") == 1
    assert "\\textbf{Microservices" not in _core_text(result.tex)


def test_unplaced_keyword_goes_to_new_labelled_line():
    result = tailor(SAMPLE, "Looking for Kafka experience", include_keywords=["Kafka"],
                    placements=[{"keyword": "Kafka", "subsection": None, "new_label": "Streaming"}])
    assert "\\item \\textbf{Streaming:} Kafka" in _core_text(result.tex)


def test_placement_to_missing_line_is_rejected():
    import pytest
    from app.tailor import AdditionError
    with pytest.raises(AdditionError):
        tailor(SAMPLE, "Looking for Kafka experience", include_keywords=["Kafka"],
               placements=[{"keyword": "Kafka", "subsection": 99}])


def test_experience_only_keyword_stays_out_of_core():
    result = tailor(SAMPLE, "Looking for Kafka experience", include_keywords=["Kafka"],
                    placements=[{"keyword": "Kafka", "skip": True}])
    assert "Kafka" not in result.core_keywords
    assert "Kafka" not in _core_text(result.tex)
