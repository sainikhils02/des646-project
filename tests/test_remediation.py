"""Tests for the remediation engine (rule-based fallback)."""
from design_assistant.remediation import RemediationEngine, RemediationReport, RemediationSuggestion


def test_empty_issues():
    engine = RemediationEngine()
    report = engine.generate(issues=[])
    assert len(report.suggestions) == 0
    assert report.total_predicted_dfs_delta == 0.0


def test_rule_based_generates_suggestions():
    engine = RemediationEngine()
    issues = [
        {
            "category": "screen_reader",
            "severity": "critical",
            "description": "3 image(s) lack alt text",
            "element_info": "img.hero",
        },
        {
            "category": "keyboard",
            "severity": "serious",
            "description": "No skip-navigation link found",
        },
        {
            "category": "functional",
            "severity": "serious",
            "description": "Page does not declare a language",
        },
    ]
    report = engine.generate(issues=issues)
    assert len(report.suggestions) == 3
    assert all(isinstance(s, RemediationSuggestion) for s in report.suggestions)


def test_suggestion_has_impact():
    engine = RemediationEngine()
    issues = [{"category": "contrast", "severity": "moderate", "description": "Low contrast region"}]
    report = engine.generate(issues=issues)
    assert len(report.suggestions) == 1
    impact = report.suggestions[0].predicted_impact
    assert "technical" in impact
    assert "perceptual" in impact
    assert "ethical" in impact


def test_report_serialization():
    engine = RemediationEngine()
    issues = [{"category": "accessibility", "severity": "serious", "description": "Button without name"}]
    report = engine.generate(issues=issues)
    d = report.to_dict()
    assert "suggestions" in d
    assert "summary" in d
    assert "total_predicted_dfs_delta" in d
