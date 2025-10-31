"""Accessibility auditing via axe-core."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

try:
    from axe_selenium_python import Axe
except ImportError:  # pragma: no cover - optional dependency
    Axe = None


@dataclass(frozen=True)
class AccessibilityViolation:
    """Represents a single axe-core violation."""

    violation_id: str
    impact: Optional[str]
    description: str
    help_url: Optional[str]
    nodes: List[str]


@dataclass(frozen=True)
class AccessibilityReport:
    """Summary of accessibility findings."""

    score: float
    violations: List[AccessibilityViolation]
    raw_results: Optional[dict]

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "violations": [violation.__dict__ for violation in self.violations],
            "raw_results": self.raw_results,
        }


class AccessibilityAuditor:
    """Runs axe-core and converts results into structured reports."""

    def __init__(self, *, baseline: int = 25) -> None:
        self.baseline = max(baseline, 1)

    def audit(self, driver: Any) -> AccessibilityReport:
        if Axe is None:
            raise RuntimeError(
                "axe-selenium-python is not installed. Install it to run accessibility audits."
            )
        axe = Axe(driver)
        axe.inject()
        results = axe.run()
        return self.audit_from_raw(results)

    def audit_from_raw(self, results: Optional[dict]) -> AccessibilityReport:
        violations_json = (results or {}).get("violations", []) if results else []
        violations = [
            AccessibilityViolation(
                violation_id=item.get("id", "unknown"),
                impact=item.get("impact"),
                description=item.get("description", ""),
                help_url=item.get("helpUrl"),
                nodes=[node.get("html", "") for node in item.get("nodes", [])],
            )
            for item in violations_json
        ]
        penalty = len(violations) / self.baseline
        score = max(0.0, 1.0 - penalty)
        return AccessibilityReport(score=score, violations=violations, raw_results=results)
