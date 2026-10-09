from app.catalog import GROUPS, group_in_text, groups_in_text

BY_LABEL = {g.label: g for g in GROUPS}


def test_synonyms_match_each_other():
    # JD says Golang, resume says Go: that is a real match, not a gap.
    assert group_in_text(BY_LABEL["Go"], "Built services in Go.")
    assert group_in_text(BY_LABEL["Go"], "Experienced with Golang tooling.")
    assert group_in_text(BY_LABEL["Kubernetes"], "Ran K8s in production.")


def test_go_is_case_sensitive_so_prose_does_not_match():
    assert not group_in_text(BY_LABEL["Go"], "We will go live next week.")


def test_short_all_caps_aliases_are_case_sensitive():
    assert not group_in_text(BY_LABEL["Disaster Recovery"], "Dr. Smith joined the team.")
    assert group_in_text(BY_LABEL["Disaster Recovery"], "Designed the DR runbook.")


def test_whole_word_only():
    assert not group_in_text(BY_LABEL["Git"], "Maintained GitHub Actions workflows.")


def test_groups_in_text_returns_labels_once():
    labels = [g.label for g in groups_in_text("Terraform and Terraform again, plus AWS.")]
    assert labels.count("Terraform") == 1
    assert "AWS" in labels
