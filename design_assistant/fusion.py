"""Utilities for combining audit subscores into a unified hierarchical fairness score."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class TierScore:
    """Represents a single tier in the hierarchical DFS."""

    name: str
    value: float
    weight: float
    sub_scores: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "weight": self.weight,
            "sub_scores": self.sub_scores,
        }


@dataclass(frozen=True)
class DesignFairnessScore:
    """Hierarchical Design Fairness Score (DFS).

    Three-tier structure:
        Technical  = weighted(accessibility, keyboard_nav, screen_reader)
        Perceptual = weighted(contrast, visual_hierarchy)
        Ethical    = weighted(dark_pattern, transparency)

    DFS = w_tech · S_technical + w_perc · S_perceptual + w_eth · S_ethical

    A gating mechanism penalises the composite score when the technical tier
    falls below a threshold, reflecting that inaccessible interfaces cannot
    meaningfully score well on perception or ethics.
    """

    technical: TierScore
    perceptual: TierScore
    ethical: TierScore
    gate_threshold: float = 0.3

    # ---- legacy fields kept for backward compatibility ----
    accessibility_score: Optional[float] = None
    ethical_ux_score: float = 0.0
    alpha: float = 0.4
    beta: float = 0.3

    @property
    def value(self) -> float:
        raw = (
            self.technical.value * self.technical.weight
            + self.perceptual.value * self.perceptual.weight
            + self.ethical.value * self.ethical.weight
        )
        normalizer = self.technical.weight + self.perceptual.weight + self.ethical.weight
        if normalizer == 0:
            return 0.0
        composite = raw / normalizer

        # Gating: if technical score is very low, cap the final score
        if self.technical.value < self.gate_threshold:
            gate_factor = self.technical.value / self.gate_threshold
            composite *= gate_factor

        return max(0.0, min(1.0, composite))

    @classmethod
    def from_components(
        cls,
        *,
        accessibility_score: Optional[float] = None,
        ethical_score: float = 0.0,
        contrast_score: Optional[float] = None,
        keyboard_score: Optional[float] = None,
        screen_reader_score: Optional[float] = None,
        alpha: float = 0.4,
        beta: float = 0.3,
    ) -> "DesignFairnessScore":
        """Build a hierarchical DFS from individual component scores.

        Parameters
        ----------
        accessibility_score : axe-core based WCAG compliance score [0,1]
        ethical_score : dark-pattern / ethical UX score [0,1]
        contrast_score : visual contrast adequacy score [0,1]
        keyboard_score : keyboard-only navigation score [0,1]
        screen_reader_score : ARIA / screen-reader simulation score [0,1]
        alpha, beta : kept for backward API compat; gamma = 1 - alpha - beta
        """
        gamma = max(0.0, 1.0 - alpha - beta)

        # --- Technical tier ---
        tech_subs: Dict[str, float] = {}
        if accessibility_score is not None:
            tech_subs["accessibility"] = accessibility_score
        if keyboard_score is not None:
            tech_subs["keyboard_navigation"] = keyboard_score
        if screen_reader_score is not None:
            tech_subs["screen_reader"] = screen_reader_score

        if tech_subs:
            # Give accessibility 50%, keyboard 25%, screen-reader 25%
            weights = {"accessibility": 0.50, "keyboard_navigation": 0.25, "screen_reader": 0.25}
            present_weights = {k: weights.get(k, 1.0) for k in tech_subs}
            w_sum = sum(present_weights.values())
            tech_value = sum(tech_subs[k] * present_weights[k] for k in tech_subs) / w_sum if w_sum else 0.0
        else:
            tech_value = 0.0

        technical = TierScore(
            name="Technical Accessibility",
            value=tech_value,
            weight=alpha,
            sub_scores=tech_subs,
        )

        # --- Perceptual tier ---
        perc_subs: Dict[str, float] = {}
        if contrast_score is not None:
            perc_subs["contrast"] = contrast_score
        # visual_hierarchy could be added later
        perc_value = sum(perc_subs.values()) / len(perc_subs) if perc_subs else 0.0

        perceptual = TierScore(
            name="Perceptual Quality",
            value=perc_value,
            weight=gamma,
            sub_scores=perc_subs,
        )

        # --- Ethical tier ---
        eth_subs: Dict[str, float] = {"dark_patterns": ethical_score}
        ethical_tier = TierScore(
            name="Ethical Design",
            value=ethical_score,
            weight=beta,
            sub_scores=eth_subs,
        )

        return cls(
            technical=technical,
            perceptual=perceptual,
            ethical=ethical_tier,
            accessibility_score=accessibility_score,
            ethical_ux_score=ethical_score,
            alpha=alpha,
            beta=beta,
        )

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "technical": self.technical.to_dict(),
            "perceptual": self.perceptual.to_dict(),
            "ethical": self.ethical.to_dict(),
            "gate_threshold": self.gate_threshold,
            # Legacy keys for backward compatibility
            "accessibility_score": self.accessibility_score,
            "ethical_ux_score": self.ethical_ux_score,
            "alpha": self.alpha,
            "beta": self.beta,
        }
