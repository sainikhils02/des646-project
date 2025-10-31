"""Utilities for combining audit subscores into a unified fairness score."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DesignFairnessScore:
    """Represents the aggregated fairness score and its components."""

    accessibility_score: Optional[float]
    ethical_ux_score: float
    alpha: float
    beta: float

    @property
    def value(self) -> float:
        weighted_accessibility = (self.accessibility_score or 0.0) * self.alpha
        weighted_ethics = self.ethical_ux_score * self.beta
        normalizer = (self.alpha if self.accessibility_score is not None else 0.0) + self.beta
        if normalizer == 0:
            return 0.0
        return (weighted_accessibility + weighted_ethics) / normalizer

    @classmethod
    def from_components(
        cls,
        *,
        accessibility_score: Optional[float],
        ethical_score: float,
        alpha: float,
        beta: float,
    ) -> "DesignFairnessScore":
        return cls(
            accessibility_score=accessibility_score,
            ethical_ux_score=ethical_score,
            alpha=alpha,
            beta=beta,
        )

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "accessibility_score": self.accessibility_score,
            "ethical_ux_score": self.ethical_ux_score,
            "alpha": self.alpha,
            "beta": self.beta,
        }
