"""Tests for the hierarchical Design Fairness Score."""
from design_assistant.fusion import DesignFairnessScore, TierScore


def test_from_components_all_scores():
    dfs = DesignFairnessScore.from_components(
        accessibility_score=0.9,
        ethical_score=0.8,
        contrast_score=0.7,
        keyboard_score=0.85,
        screen_reader_score=0.75,
        alpha=0.4,
        beta=0.3,
    )
    assert 0.0 <= dfs.value <= 1.0
    assert dfs.technical.value > 0
    assert dfs.perceptual.value > 0
    assert dfs.ethical.value > 0


def test_from_components_missing_agentic():
    """Without agentic scores, only accessibility contributes to technical."""
    dfs = DesignFairnessScore.from_components(
        accessibility_score=0.9,
        ethical_score=0.8,
        contrast_score=0.6,
    )
    assert dfs.value > 0
    assert dfs.technical.value == 0.9  # only accessibility, full weight


def test_gating_mechanism():
    """When technical score is very low, composite is penalised."""
    low_tech = DesignFairnessScore.from_components(
        accessibility_score=0.1,
        ethical_score=0.95,
        contrast_score=0.95,
    )
    high_tech = DesignFairnessScore.from_components(
        accessibility_score=0.9,
        ethical_score=0.95,
        contrast_score=0.95,
    )
    # The gating should make low_tech.value noticeably lower
    assert low_tech.value < high_tech.value


def test_all_zeros():
    dfs = DesignFairnessScore.from_components(
        accessibility_score=0.0,
        ethical_score=0.0,
        contrast_score=0.0,
        keyboard_score=0.0,
        screen_reader_score=0.0,
    )
    assert dfs.value == 0.0


def test_all_ones():
    dfs = DesignFairnessScore.from_components(
        accessibility_score=1.0,
        ethical_score=1.0,
        contrast_score=1.0,
        keyboard_score=1.0,
        screen_reader_score=1.0,
    )
    assert dfs.value == 1.0


def test_to_dict_structure():
    dfs = DesignFairnessScore.from_components(
        accessibility_score=0.8,
        ethical_score=0.7,
    )
    d = dfs.to_dict()
    assert "value" in d
    assert "technical" in d
    assert "perceptual" in d
    assert "ethical" in d
    assert "sub_scores" in d["technical"]


def test_backward_compat_fields():
    dfs = DesignFairnessScore.from_components(
        accessibility_score=0.8,
        ethical_score=0.7,
        alpha=0.5,
        beta=0.3,
    )
    assert dfs.alpha == 0.5
    assert dfs.beta == 0.3
    assert dfs.accessibility_score == 0.8
    assert dfs.ethical_ux_score == 0.7
