import re

from app.analyzer import analyze



def _terms(analysis):
    return [s.term.lower() for s in analysis.suggestions]


def test_suggestions_are_never_already_in_resume(resume_md, jd_text):
    result = analyze(resume_md, jd_text, max_suggestions=30)
    lowered_resume = resume_md.lower()
    for suggestion in result.suggestions:
        # Whole-word check: "data" is fine when the resume only says "database".
        assert not re.search(rf"(?<![a-z0-9]){re.escape(suggestion.term.lower())}(?![a-z0-9])", lowered_resume)


def test_known_technology_terms_are_suggested(resume_md, jd_text):
    result = analyze(resume_md, jd_text, max_suggestions=30)
    terms = _terms(result)
    assert "terraform" in terms
    assert "kubernetes" in terms
    assert "prometheus" in terms


def test_existing_skills_are_not_suggested(resume_md, jd_text):
    result = analyze(resume_md, jd_text, max_suggestions=30)
    terms = _terms(result)
    assert "powershell" not in terms
    assert "postgresql" not in terms


def test_skills_already_in_resume_are_reported_as_covered(resume_md, jd_text):
    result = analyze(resume_md, jd_text, max_suggestions=30)
    covered = {s.term.lower() for s in result.covered}
    assert "postgresql" in covered
    assert "powershell" in covered
    assert covered.isdisjoint(set(_terms(result)))


def test_synonym_in_resume_counts_as_covered():
    resume = "# Jane\n\n## Skills\n\n- Go, K8s, Terraform\n"
    jd = "We need Golang and Kubernetes experience with Terraform on AWS and Docker pipelines daily " \
         "for the platform team across many services and regions around the world."
    result = analyze(resume, jd, max_suggestions=30)
    covered = {s.term for s in result.covered}
    assert {"Go", "Kubernetes", "Terraform"} <= covered
    assert "Go" not in {s.term for s in result.suggestions}


def test_stopword_only_phrases_are_never_returned(resume_md, jd_text):
    result = analyze(resume_md, jd_text, max_suggestions=30)
    for term in _terms(result):
        assert term not in {"and", "the", "to of", "with"}
        assert " to " not in f" {term} "


def test_max_suggestions_is_respected(resume_md, jd_text):
    assert len(analyze(resume_md, jd_text, max_suggestions=5).suggestions) <= 5


def test_suggestions_sorted_by_score_descending(resume_md, jd_text):
    scores = [s.score for s in analyze(resume_md, jd_text, max_suggestions=30).suggestions]
    assert scores == sorted(scores, reverse=True)


def test_match_percentages_are_bounded(resume_md, jd_text):
    result = analyze(resume_md, jd_text, max_suggestions=30)
    assert 0 <= result.match_before <= 100
    everything = [s.term for s in result.suggestions]
    assert result.match_before <= result.match_after(everything) <= 100


def test_empty_jd_yields_no_suggestions(resume_md):
    result = analyze(resume_md, "", max_suggestions=30)
    assert result.suggestions == []
    assert result.match_before == 0.0
