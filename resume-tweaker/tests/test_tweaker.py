from app.tweaker import apply_keywords, extract_name


def _apply(markdown, terms, reorder=False, jd_terms=()):
    return apply_keywords(markdown, terms, reorder=reorder, jd_terms=list(jd_terms))


def test_nothing_selected_and_no_reorder_returns_input_unchanged(resume_md):
    assert _apply(resume_md, []).markdown == resume_md


def test_accepted_terms_appear_exactly_once(resume_md):
    result = _apply(resume_md, ["Terraform", "Kubernetes"])
    assert result.markdown.count("Terraform") == 1
    assert result.markdown.count("Kubernetes") == 1


def test_unaccepted_terms_never_appear(resume_md):
    result = _apply(resume_md, ["Terraform"])
    assert "Kubernetes" not in result.markdown
    assert "Prometheus" not in result.markdown


def test_core_competencies_section_is_created_after_summary(resume_md):
    result = _apply(resume_md, ["Terraform"])
    lines = result.markdown.split("\n")
    summary_at = lines.index("## Professional Summary")
    core_at = lines.index("## Core Competencies")
    skills_at = lines.index("## Skills")
    assert summary_at < core_at < skills_at
    assert "- Terraform" in lines


def test_keywords_are_chunked_four_per_line(resume_md):
    result = _apply(resume_md, ["A1", "B2", "C3", "D4", "E5"])
    assert "- A1 | B2 | C3 | D4" in result.markdown
    assert "- E5" in result.markdown
    assert result.marked_lines == {"- A1 | B2 | C3 | D4", "- E5"}


def test_existing_core_competencies_section_is_extended():
    markdown = "# Jane\n\n## Core Competencies\n\n- AWS | Docker\n\n## Experience\n\n- Did things.\n"
    result = _apply(markdown, ["Terraform"])
    assert result.markdown.count("## Core Competencies") == 1
    assert "- Terraform" in result.markdown.split("## Experience")[0]


def test_keyword_already_listed_in_core_section_is_not_repeated():
    markdown = "# Jane\n\n## Core Competencies\n\n- AWS | Docker\n\n## Experience\n\n- Did things.\n"
    assert _apply(markdown, ["AWS"]).added == []


def test_only_inserted_lines_differ_from_original(resume_md):
    result = _apply(resume_md, ["Terraform", "Prometheus"])
    original = resume_md.split("\n")
    changed = result.markdown.split("\n")
    assert [line for line in original if line not in changed] == []
    added = [line for line in changed if line not in original]
    assert all(line in ("", "## Core Competencies") or "Terraform" in line or "Prometheus" in line for line in added)


def test_reorder_moves_job_relevant_bullet_first_without_changing_text():
    markdown = (
        "# Jane\n\n## Experience\n\n### Role\n\n"
        "- Wrote reports in Excel.\n"
        "- Ran Kubernetes clusters for production.\n"
        "- Filed tickets.\n"
    )
    result = _apply(markdown, [], reorder=True, jd_terms=["Kubernetes"])
    lines = result.markdown.split("\n")
    assert lines.index("- Ran Kubernetes clusters for production.") < lines.index("- Wrote reports in Excel.")
    assert sorted(lines) == sorted(markdown.split("\n"))  # same lines, only moved
    assert result.reordered_sections == 1


def test_reorder_never_crosses_job_headings():
    markdown = (
        "# Jane\n\n## Experience\n\n### Old job\n\n- Plain work.\n\n### New job\n\n"
        "- Kubernetes work.\n"
    )
    result = _apply(markdown, [], reorder=True, jd_terms=["Kubernetes"])
    assert result.markdown.index("### Old job") < result.markdown.index("- Plain work.")
    assert result.markdown.index("- Plain work.") < result.markdown.index("### New job")


def test_reorder_leaves_non_matching_sections_alone():
    markdown = "# Jane\n\n## Hobbies\n\n- Zebra watching.\n- Apple picking.\n"
    result = _apply(markdown, [], reorder=True, jd_terms=["Apple"])
    assert result.markdown == markdown


def test_extract_name_from_first_heading(resume_md):
    assert extract_name(resume_md) == "Jane Doe"
    assert extract_name("no heading here") == "Resume"
