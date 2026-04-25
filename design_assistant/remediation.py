from __future__ import annotations

import json
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None


@dataclass(frozen=True)
class RemediationSuggestion:
    """A single predicted fix with trade-off metadata."""

    issue_id: str
    issue_category: str        # "accessibility" | "contrast" | "dark_pattern" | "keyboard" | "screen_reader"
    issue_description: str
    original_html: str
    fixed_html: str
    explanation: str
    priority: str              # "high" | "medium" | "low"
    predicted_impact: Dict[str, float]   # { "technical": +0.05, "perceptual": 0.0, "ethical": -0.02 }
    trade_off_note: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "issue_category": self.issue_category,
            "issue_description": self.issue_description,
            "original_html": self.original_html,
            "fixed_html": self.fixed_html,
            "explanation": self.explanation,
            "priority": self.priority,
            "predicted_impact": self.predicted_impact,
            "trade_off_note": self.trade_off_note,
        }


@dataclass
class RemediationReport:
    """All remediation suggestions for a single audit run."""

    suggestions: List[RemediationSuggestion]
    summary: str
    total_predicted_dfs_delta: float

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "total_predicted_dfs_delta": self.total_predicted_dfs_delta,
            "suggestion_count": len(self.suggestions),
            "suggestions": [s.to_dict() for s in self.suggestions],
        }


class RemediationEngine:
    """Generates code-level remediation suggestions using an LLM.""" 

    def __init__(self, *, llm_config: Optional[Any] = None) -> None:
        self._model = None
        self._config = llm_config

        if genai is not None and llm_config and getattr(llm_config, "api_key", None):
            try:
                genai.configure(api_key=llm_config.api_key)
                model_name = getattr(llm_config, "model", "models/gemini-2.5-pro")
                self._model = genai.GenerativeModel(model_name)
            except Exception as exc:
                print(f"RemediationEngine: Could not initialise LLM: {exc}")

    @property
    def is_available(self) -> bool:
        return self._model is not None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        issues: List[Dict[str, Any]],
        html_snippet: str = "",
        url: Optional[str] = None,
        current_scores: Optional[Dict[str, float]] = None,
    ) -> RemediationReport:
        """Generate remediation suggestions for detected issues.

        Parameters
        ----------
        issues : list of dicts with keys ``category``, ``description``,
                 ``element_info``, ``severity``, ``wcag_criterion``, etc.
        html_snippet : a representative HTML excerpt from the page
        url : the audited URL (for context)
        current_scores : current DFS sub-scores for computing deltas
        """
        if not issues:
            return RemediationReport(
                suggestions=[], summary="No issues to remediate.", total_predicted_dfs_delta=0.0
            )

        if self.is_available:
            return self._generate_via_llm(
                issues=issues,
                html_snippet=html_snippet,
                url=url,
                current_scores=current_scores or {},
            )
        else:
            return self._generate_rule_based(
                issues=issues,
                current_scores=current_scores or {},
            )

    # ------------------------------------------------------------------
    # LLM-based generation
    # ------------------------------------------------------------------

    def _generate_via_llm(
        self,
        *,
        issues: List[Dict[str, Any]],
        html_snippet: str,
        url: Optional[str],
        current_scores: Dict[str, float],
    ) -> RemediationReport:
        """Ask the LLM for structured remediation JSON."""
        # Limit to top-priority issues to avoid prompt bloat
        priority_issues = sorted(
            issues,
            key=lambda i: {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}.get(
                i.get("severity", "minor"), 4
            ),
        )[:10]

        prompt = textwrap.dedent(f"""\
            You are a web accessibility and ethical UX remediation specialist.

            Given the following issues detected on a web page, generate minimal
            code fixes (HTML/CSS/ARIA) for each.  For every fix, estimate the
            impact on these three Design Fairness Score dimensions:
            - technical (accessibility / keyboard / screen-reader)
            - perceptual (contrast / visual hierarchy)
            - ethical (dark patterns / transparency)

            Express impact as a float delta in [-0.1, +0.1].
            If a fix helps one dimension but might hurt another, include a
            ``trade_off_note`` explaining the tension.

            URL: {url or "N/A"}

            Current scores:
            {json.dumps(current_scores, indent=2)}

            Issues (JSON):
            {json.dumps(priority_issues, indent=2, ensure_ascii=False)}

            HTML excerpt (truncated):
            ```html
            {html_snippet[:3000]}
            ```

            Respond with strict JSON matching this schema (NO text outside JSON):
            {{
              "suggestions": [
                {{
                  "issue_id": "<category>_<index>",
                  "issue_category": "accessibility|contrast|dark_pattern|keyboard|screen_reader",
                  "issue_description": "...",
                  "original_html": "<code before>",
                  "fixed_html": "<code after>",
                  "explanation": "...",
                  "priority": "high|medium|low",
                  "predicted_impact": {{"technical": 0.0, "perceptual": 0.0, "ethical": 0.0}},
                  "trade_off_note": "..." or null
                }}
              ],
              "summary": "one-paragraph overview",
              "total_predicted_dfs_delta": <float>
            }}
        """)

        try:
            response = self._model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 4000,
                },
            )
            raw_text = (response.text or "").strip()
            data = self._parse_json(raw_text)
            if data:
                return self._dict_to_report(data)
        except Exception as exc:
            print(f"RemediationEngine LLM error: {exc}")

        # Fallback
        return self._generate_rule_based(issues=issues, current_scores=current_scores)

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    _TEMPLATES: Dict[str, Dict[str, str]] = {
        "images_without_alt": {
            "original": '<img src="...">',
            "fixed": '<img src="..." alt="Descriptive text">',
            "explanation": "Add descriptive alt text for screen reader users.",
            "priority": "high",
        },
        "buttons_without_name": {
            "original": "<button><svg>...</svg></button>",
            "fixed": '<button aria-label="Action description"><svg>...</svg></button>',
            "explanation": "Add aria-label so screen readers can announce the button purpose.",
            "priority": "high",
        },
        "inputs_without_label": {
            "original": '<input type="text" id="email">',
            "fixed": '<label for="email">Email</label>\n<input type="text" id="email">',
            "explanation": "Associate a <label> with the input using the for/id pattern.",
            "priority": "high",
        },
        "no_skip_link": {
            "original": "<body>...",
            "fixed": '<body>\n  <a href="#main-content" class="skip-link">Skip to main content</a>\n  ...\n  <main id="main-content">',
            "explanation": "Add a skip-navigation link so keyboard users can bypass repetitive navigation.",
            "priority": "medium",
        },
        "no_lang": {
            "original": "<html>",
            "fixed": '<html lang="en">',
            "explanation": "Declare the page language so screen readers use correct pronunciation.",
            "priority": "medium",
        },
        "no_visible_focus": {
            "original": "button { outline: none; }",
            "fixed": "button:focus-visible { outline: 2px solid #005fcc; outline-offset: 2px; }",
            "explanation": "Restore visible focus indicators for keyboard users.",
            "priority": "high",
        },
        "zoom_disabled": {
            "original": '<meta name="viewport" content="... user-scalable=no, maximum-scale=1">',
            "fixed": '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "explanation": "Allow users to zoom the page for readability.",
            "priority": "high",
        },
    }

    def _generate_rule_based(
        self,
        *,
        issues: List[Dict[str, Any]],
        current_scores: Dict[str, float],
    ) -> RemediationReport:
        """Generate remediation using hardcoded templates."""
        suggestions: List[RemediationSuggestion] = []

        for idx, issue in enumerate(issues[:15]):
            desc = issue.get("description", "")
            category = issue.get("category", "accessibility")

            template_key = self._match_template(desc)
            if template_key and template_key in self._TEMPLATES:
                tmpl = self._TEMPLATES[template_key]
            else:
                tmpl = {
                    "original": issue.get("element_info", "N/A"),
                    "fixed": f"Fix: {issue.get('recommendation', 'Review and address this issue.')}",
                    "explanation": desc,
                    "priority": self._severity_to_priority(issue.get("severity", "moderate")),
                }

            impact = self._estimate_impact(category)

            suggestions.append(RemediationSuggestion(
                issue_id=f"{category}_{idx}",
                issue_category=category,
                issue_description=desc,
                original_html=tmpl["original"],
                fixed_html=tmpl["fixed"],
                explanation=tmpl["explanation"],
                priority=tmpl["priority"],
                predicted_impact=impact,
            ))

        total_delta = sum(
            sum(s.predicted_impact.values()) for s in suggestions
        )

        return RemediationReport(
            suggestions=suggestions,
            summary=f"Generated {len(suggestions)} remediation suggestions for {len(issues)} detected issues.",
            total_predicted_dfs_delta=round(total_delta, 3),
        )

    def _match_template(self, description: str) -> Optional[str]:
        desc_lower = description.lower()
        mappings = {
            "alt text": "images_without_alt",
            "alt attribute": "images_without_alt",
            "image": "images_without_alt",
            "button": "buttons_without_name",
            "accessible name": "buttons_without_name",
            "label": "inputs_without_label",
            "skip": "no_skip_link",
            "bypass": "no_skip_link",
            "language": "no_lang",
            "lang": "no_lang",
            "focus": "no_visible_focus",
            "outline": "no_visible_focus",
            "zoom": "zoom_disabled",
            "user-scalable": "zoom_disabled",
            "maximum-scale": "zoom_disabled",
        }
        for keyword, key in mappings.items():
            if keyword in desc_lower:
                return key
        return None

    @staticmethod
    def _severity_to_priority(severity: str) -> str:
        return {"critical": "high", "serious": "high", "moderate": "medium"}.get(severity, "low")

    @staticmethod
    def _estimate_impact(category: str) -> Dict[str, float]:
        return {
            "accessibility": {"technical": 0.04, "perceptual": 0.0, "ethical": 0.01},
            "keyboard": {"technical": 0.03, "perceptual": 0.0, "ethical": 0.0},
            "screen_reader": {"technical": 0.04, "perceptual": 0.0, "ethical": 0.0},
            "contrast": {"technical": 0.0, "perceptual": 0.05, "ethical": 0.0},
            "dark_pattern": {"technical": 0.0, "perceptual": 0.0, "ethical": 0.05},
            "functional": {"technical": 0.02, "perceptual": 0.01, "ethical": 0.0},
        }.get(category, {"technical": 0.01, "perceptual": 0.01, "ethical": 0.01})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json(raw: str) -> Optional[dict]:
        import re
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    @staticmethod
    def _dict_to_report(data: dict) -> RemediationReport:
        suggestions = []
        for item in data.get("suggestions", []):
            suggestions.append(RemediationSuggestion(
                issue_id=item.get("issue_id", "unknown"),
                issue_category=item.get("issue_category", "accessibility"),
                issue_description=item.get("issue_description", ""),
                original_html=item.get("original_html", ""),
                fixed_html=item.get("fixed_html", ""),
                explanation=item.get("explanation", ""),
                priority=item.get("priority", "medium"),
                predicted_impact=item.get("predicted_impact", {"technical": 0, "perceptual": 0, "ethical": 0}),
                trade_off_note=item.get("trade_off_note"),
            ))
        return RemediationReport(
            suggestions=suggestions,
            summary=data.get("summary", ""),
            total_predicted_dfs_delta=data.get("total_predicted_dfs_delta", 0.0),
        )
