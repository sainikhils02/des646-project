"""LLM integration for enhanced report generation using Google Gemini 2.0 Flash."""
from __future__ import annotations

import json
import os
import re
import textwrap
from dataclasses import dataclass
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None


@dataclass
class LLMConfig:
    """Configuration for LLM integration."""
    
    api_key: Optional[str] = None
    model: str = "models/gemini-2.5-pro"
    temperature: float = 0.7
    max_tokens: int = 8000
    custom_prompt_template: Optional[str] = None
    
    def __post_init__(self):
        """Load API key from environment if not provided."""
        if self.api_key is None:
            self.api_key = os.getenv("GOOGLE_API_KEY")


class LLMAnalyzer:
    """Analyzes design audits using Google Gemini 2.0 Flash for enhanced insights."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM analyzer.
        
        Args:
            config: LLM configuration (API key, model, etc.)
        """
        self.config = config or LLMConfig()
        self._model = None
        
        print(f"DEBUG INIT: genai module available: {genai is not None}")
        print(f"DEBUG INIT: API key present: {self.config.api_key is not None}")
        print(f"DEBUG INIT: API key value (first 10 chars): {self.config.api_key[:10] if self.config.api_key else 'None'}")
        print(f"DEBUG INIT: Model: {self.config.model}")
        
        if genai is not None and self.config.api_key:
            try:
                genai.configure(api_key=self.config.api_key)
                self._model = genai.GenerativeModel(self.config.model)
                print(f"DEBUG INIT: Model initialized successfully")
            except Exception as e:
                print(f"DEBUG INIT: Failed to initialize model: {e}")
        else:
            if genai is None:
                print(f"DEBUG INIT: genai module not available - install google-generativeai")
            if not self.config.api_key:
                print(f"DEBUG INIT: No API key provided")
    
    def is_available(self) -> bool:
        """Check if LLM is available for use."""
        return self._model is not None
    
    def analyze_comprehensive(
        self,
        screenshot_path: Optional[str] = None,
        html_content: Optional[str] = None,
        url: Optional[str] = None,
        accessibility_data: Optional[dict] = None,
        contrast_data: Optional[dict] = None,
        dark_pattern_data: Optional[dict] = None,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Perform comprehensive multimodal analysis using screenshot and HTML.
        
        Args:
            screenshot_path: Path to screenshot image
            html_content: Raw HTML content
            url: URL being analyzed
            accessibility_data: Computed accessibility metrics
            contrast_data: Computed contrast metrics
            dark_pattern_data: Computed dark pattern metrics
            custom_prompt: Optional custom prompt
            
        Returns:
            Comprehensive LLM-generated analysis
        """
        if not self.is_available():
            print("DEBUG LLM: LLM not available")
            return ""
        
        print(f"DEBUG LLM: Starting comprehensive analysis")
        print(f"DEBUG LLM: Screenshot path: {screenshot_path}")
        print(f"DEBUG LLM: Has HTML: {html_content is not None}")
        
        try:
            from PIL import Image as PILImage
            print(f"DEBUG LLM: PIL.Image imported successfully")
            
            # Build comprehensive prompt
            prompt_parts = []
            
            # Add system instruction
            prompt_parts.append(
            """
                You are a specialist UX auditor focusing on accessibility, visual design, and ethical user experience.

                Given a website (via screenshot, HTML structure, and automated audit metrics), deliver a detailed and structured audit covering:

                1. Accessibility & WCAG Compliance
                - Evaluate against WCAG 2.1 (Level A/AA/AAA as applicable).
                - Verify full keyboard accessibility.
                - Check screen-reader compatibility: semantic HTML, ARIA roles, labels.
                - Confirm visual accessibility: contrast ratio, text size, zoom/scaling behavior.
                - Verify alternative text for images/icons and captions/transcripts for media.
                - Ensure logical focus order and visible focus indicators.
                - Avoid conveying meaning using color alone.
                - Flag barriers that prevent users with disabilities from completing tasks.

                2. Visual Design & Contrast
                - Evaluate typography: size, line height, readability.
                - Check colour contrast (minimum 4.5:1 for body text per WCAG).
                - Review layout consistency, spacing, alignment, visual hierarchy.
                - Verify responsive behavior across breakpoints.
                - Identify unnecessary animations or visual noise.
                - Check brand/design consistency: buttons, icons, spacing, padding.
                - Assess clarity and visibility of calls-to-action.

                3. Ethical UX & Dark Patterns
                - Detect manipulative UI patterns: forced sign-ups, misleading defaults, urgency pressure.
                - Evaluate transparency for pricing and data collection.
                - Confirm respect for user agency: undo options, cancellation clarity, clear exits.
                - Assess privacy/accessibility fairness and ensure no coercive UI behaviors.

                4. Prioritized Recommendations
                For each issue identified:
                - Specify actionable recommendation.
                - Assign priority: High / Medium / Low.
                - Explain user impact and risk.
                - Provide quick wins and longer-term fixes.

                5. Overall Summary
                - Provide an executive summary with key strengths and critical issues.
                - Suggest a roadmap: example → fix accessibility blockers → refine visual hierarchy → re-check ethical UX patterns.
            """
            )

            
            # Add context
            if url:
                prompt_parts.append(f"\n## Website URL\n{url}\n")
            
            # Add computed metrics for context
            if accessibility_data:
                prompt_parts.append(f"""
## Automated Accessibility Metrics
- Score: {accessibility_data.get('score', 'N/A')}
- Total Violations: {accessibility_data.get('violation_count', 0)}
- Critical Issues: {accessibility_data.get('critical_count', 0)}
""")
            
            if contrast_data:
                prompt_parts.append(f"""
## Automated Contrast Metrics
- Average Contrast Ratio: {contrast_data.get('avg_contrast', 'N/A')}:1
- Low-Contrast Regions: {contrast_data.get('violation_count', 0)}
""")
            
            if dark_pattern_data:
                prompt_parts.append(f"""
## Automated Dark Pattern Detection
- Ethical UX Score: {dark_pattern_data.get('score', 'N/A')}
- Detected Patterns: {dark_pattern_data.get('pattern_count', 0)}
""")
            
            # Add HTML structure (truncated if too long)
            if html_content:
                html_truncated = html_content[:15000] if len(html_content) > 15000 else html_content
                prompt_parts.append(f"""
## HTML Structure
```html
{html_truncated}
```
{"(HTML truncated to first 15,000 characters)" if len(html_content) > 15000 else ""}
""")            
            # Add analysis request
            prompt_parts.append(
                """
                You are a specialist UX auditor focusing on accessibility, visual design, and ethical user experience.

                Using the screenshot, HTML structure, and automated audit metrics, produce a structured UX audit.

                Deliver the report with the following sections:

                ## 1. Executive Summary
                - State overall UX and accessibility quality.
                - Identify key findings and critical usability or accessibility issues.

                ## 2. Accessibility Analysis (WCAG aligned)
                - Identify clear accessibility barriers.
                - Map each issue to relevant WCAG 2.1 guideline (A/AA/AAA).
                - Evaluate keyboard-only navigation, screen reader semantics, ARIA roles, alt text, focus order, contrast, and color reliance.
                - Explain how these issues affect users with disabilities.

                ## 3. Visual Design & Contrast
                - Check contrast ratios and text readability.
                - Evaluate typography: hierarchy, font size, spacing.
                - Assess layout, alignment, responsiveness, visual noise, and clarity of CTAs.

                ## 4. Ethical UX & Dark Patterns
                - Identify manipulative UI patterns:
                - Hidden opt-outs
                - Forced sign-ups
                - Misleading language or urgency pressure
                - Evaluate transparency in data handling and user autonomy.

                ## 5. Prioritized Recommendations
                For every issue:
                - Actionable fix
                - Priority level (High / Medium / Low)
                - User impact explanation
                - Quick wins vs long-term fixes

                ## 6. Implementation Guidance
                - Code-level suggestions (HTML, ARIA, CSS changes).
                - Design guidance for improving clarity, fairness, and accessibility.
                - Testing strategy:
                - Keyboard navigation test
                - Screen reader test (NVDA/VoiceOver)
                - Contrast test using tooling
                """
            )

            
            # Combine prompt
            full_prompt = "".join(prompt_parts)
            
            # Build multimodal content
            content_parts = []
            
            # Add screenshot if available
            if screenshot_path and os.path.exists(screenshot_path):
                print(f"DEBUG LLM: Loading screenshot from {screenshot_path}")
                img = PILImage.open(screenshot_path)
                content_parts.append(img)
                content_parts.append("\n## Screenshot Analysis\nAbove is the screenshot of the webpage.\n")
                print(f"DEBUG LLM: Screenshot loaded successfully")
            else:
                print(f"DEBUG LLM: Screenshot not found or path invalid: {screenshot_path}")
            
            # Add text prompt
            content_parts.append(full_prompt)
            print(f"DEBUG LLM: Content parts count: {len(content_parts)}")
            
            # Query LLM with multimodal content
            print(f"DEBUG LLM: Calling multimodal query...")
            response = self._query_llm_multimodal(content_parts)
            print(f"DEBUG LLM: Response received, length: {len(response) if response else 0}")
            return response
            
        except Exception as e:
            import traceback
            error_msg = f"Comprehensive LLM Analysis Error: {str(e)}\n{traceback.format_exc()}"
            print(f"DEBUG LLM: {error_msg}")
            return error_msg
    
    def analyze_accessibility(
        self,
        violations: list,
        score: float,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Get LLM analysis of accessibility violations.
        
        Args:
            violations: List of accessibility violations
            score: Accessibility score
            custom_prompt: Optional custom prompt to override default
            
        Returns:
            LLM-generated analysis text
        """
        if not self.is_available():
            return ""
        
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self._build_accessibility_prompt(violations, score)
        
        return self._query_llm(prompt)
    
    def analyze_contrast(
        self,
        violations: list,
        avg_contrast: float,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Get LLM analysis of contrast issues.
        
        Args:
            violations: List of contrast violations
            avg_contrast: Average contrast ratio
            custom_prompt: Optional custom prompt
            
        Returns:
            LLM-generated analysis text
        """
        if not self.is_available():
            return ""
        
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self._build_contrast_prompt(violations, avg_contrast)
        
        return self._query_llm(prompt)
    
    def analyze_dark_patterns(
        self,
        flags: list,
        score: float,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Get LLM analysis of dark patterns.
        
        Args:
            flags: List of detected dark pattern flags
            score: Ethical UX score
            custom_prompt: Optional custom prompt
            
        Returns:
            LLM-generated analysis text
        """
        if not self.is_available():
            return ""
        
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self._build_dark_pattern_prompt(flags, score)
        
        return self._query_llm(prompt)
    
    def generate_recommendations(
        self,
        audit_summary: dict,
        custom_prompt: Optional[str] = None
    ) -> str:
        """Generate actionable recommendations using LLM.
        
        Args:
            audit_summary: Dictionary with audit results
            custom_prompt: Optional custom prompt
            
        Returns:
            LLM-generated recommendations
        """
        if not self.is_available():
            return ""
        
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self._build_recommendations_prompt(audit_summary)
        
        return self._query_llm(prompt)
    
    def _build_accessibility_prompt(self, violations: list, score: float) -> str:
        """Build prompt for accessibility analysis."""
        template = self.config.custom_prompt_template or """
            You are an accessibility specialist performing a WCAG 2.1 audit.

            Inputs:
            - Accessibility Score: {score:.2%}
            - Number of Violations: {count}
            - Detailed Violations: {violations_text}

            Produce a structured audit that includes:

            1. Executive Summary
            - Short evaluation of overall accessibility health.
            - Describe risk level and blockers that prevent task completion.

            2. Top 3 Critical Issues
            For each issue:
            - Identify the WCAG criterion (A / AA / AAA).
            - State the direct usability impact.
            - Explain the functional barrier created.

            3. Actionable Recommendations
            For each issue:
            - Exact fix (what code or design change is required).
            - Include examples (e.g., proper ARIA, alt text, label association, color contrast values).
            - Prioritize high-impact, low-effort changes first.

            4. Users Affected
            - Identify which user groups are impacted (screen reader users, keyboard-only users, users with low vision, cognitive load sensitivity).
            - Explain how the barrier prevents or slows task completion.

            Output requirements:
            - Clear and concise.
            - No generic phrasing; reference the violations explicitly.
            - Focus on improving access without assigning blame.
        """
        
        violations_text = "\n".join([
            f"- {v.get('violation_id', 'unknown')}: {v.get('description', 'No description')[:200]}"
            for v in violations[:10]
        ])
        
        return template.format(
            score=score,
            count=len(violations),
            violations_text=violations_text
        )
    
    def _build_contrast_prompt(self, violations: list, avg_contrast: float) -> str:
        """Build prompt for contrast analysis."""
        template = self.config.custom_prompt_template or """
            You are a visual design and accessibility specialist evaluating contrast compliance (WCAG 2.1).

            Inputs:
            - Average Contrast Ratio: {avg_contrast:.2f}:1
            - WCAG AA requirements: 4.5:1 for normal text, 3:1 for large text
            - Low-contrast regions detected: {count}
            - Violations detected:
            {violations_text}

            Produce a structured assessment:

            1. Readability Evaluation
            - Assess overall visual clarity and text readability.
            - Compare the average contrast ratio against WCAG thresholds.
            - Identify if contrast affects primary content, navigation, or interactive elements.

            2. Impact on Users
            - Explain how low contrast affects users with low vision, color-vision deficiencies, and users in high-glare environments.
            - State whether users may miss information or fail to identify interactive elements.

            3. Practical Color Palette Recommendations
            - Suggest specific color adjustments that meet WCAG AA contrast (e.g., increase text darkness, darken background, adjust brand palette).
            - Provide example contrast-safe combinations with hex values when applicable.

            4. Priority Fixes
            - Rank fixes from highest to lowest impact (e.g., primary text, navigation, buttons/CTAs, secondary UI elements).
            - Focus on high-frequency tasks and critical actions.

            Output requirements:
            - Concise, practical, design-friendly.
            - No generic advice. Reference specific violations and contrast values.
        """
        
        violations_text = "\n".join([
            f"- Region {i+1}: Contrast {v.get('contrast_ratio', 0):.2f}:1 at position {v.get('bbox', 'unknown')}"
            for i, v in enumerate(violations[:5])
        ])
        
        return template.format(
            avg_contrast=avg_contrast,
            count=len(violations),
            violations_text=violations_text
        )
    
    def _build_dark_pattern_prompt(self, flags: list, score: float) -> str:
        """Build prompt for dark pattern analysis."""
        template = self.config.custom_prompt_template or """
            You are a UX ethics specialist evaluating potentially manipulative design patterns (dark patterns).

            Inputs Provided:
            - Ethical UX Score: {score:.2%}
            - Count of Flagged Patterns: {count}
            - Detected Patterns:
            {patterns_text}

            Your task:
            Produce a structured and professional audit focused on transparency, fairness, and user trust.

            Required Output:

            1. Ethical Risk Assessment
            - Identify the ethical issues in the detected patterns.
            - State whether the design restricts user autonomy, hides information, or pressures a choice.

            2. How the Patterns Manipulate Users
            - Explain the psychological or behavioral mechanism involved (e.g., confirmshaming, misdirection, forced action).
            - Describe the user’s likely mental model and how the interface exploits it.

            3. Ethical Alternatives (Actionable)
            - Provide specific UI/UX improvements to make the design ethical and transparent.
            - Examples:
            - Replace manipulative microcopy with neutral wording.
            - Make opt-out options visible and equal in visual hierarchy.
            - Present choices without time pressure or emotional guilt.

            4. Trust & Brand Reputation Impact
            - Explain how manipulative patterns reduce long-term trust and create negative sentiment.
            - Clarify how ethical design increases loyalty, retention, and conversion quality.

            Output Style Requirements:
            - Constructive, actionable, and user-centric.
            - No blaming; focus on improvement and creating trust.
        """
        
        patterns_text = "\n".join([
            f"- {f.get('label', 'Unknown')} (confidence: {f.get('score', 0):.0%}): \"{f.get('text', '')[:150]}...\""
            for f in flags[:5]
        ])
        
        return template.format(
            score=score,
            count=len(flags),
            patterns_text=patterns_text
        )
    
    def _build_recommendations_prompt(self, audit_summary: dict) -> str:
        """Build prompt for overall recommendations."""
        template = self.config.custom_prompt_template or """
            You are a product design consultant. Use the audit data to create a strategic improvement plan.

            Inputs:
            - Overall Design Fairness Score: {fairness_score:.2f}/1.0
            - Accessibility Score: {accessibility_score}
            - Average Contrast Ratio: {contrast_ratio:.2f}:1
            - Ethical UX Score: {ethics_score:.2%}

            Key Issues Identified:
            - {accessibility_count} accessibility violations
            - {contrast_count} contrast issues
            - {dark_pattern_count} potential dark patterns

            Output Requirements:

            1. Prioritized Action Plan
            - Quick Wins (high impact, low effort)
            - Medium-term Improvements
            - Long-term Enhancements
            - Each item must include what to change and why it matters.

            2. Resource Allocation
            - Recommend how design, engineering, and accessibility resources should be distributed.
            - Call out dependencies and sequence.

            3. Implementation Timeline
            - Provide grouped estimates (e.g., 1–2 weeks, 1 month, 1+ quarter).
            - Prioritize accessibility blockers and ethical issues first.

            4. Success Metrics
            - Define measurable outcomes (reduction in violations, improved conversion without dark patterns, fewer support tickets).

            5. Team Roles Needed
            - Specify the roles required (designer, frontend developer, accessibility specialist, QA).
            - Clarify what each role is responsible for.

            Constraints:
            - Advice must be practical and execution-focused.
            - Use concise language. No filler text.
        """
        
        return template.format(
            fairness_score=audit_summary.get('fairness_score', 0),
            accessibility_score=audit_summary.get('accessibility_score', 'N/A'),
            contrast_ratio=audit_summary.get('contrast_ratio', 0),
            ethics_score=audit_summary.get('ethics_score', 0),
            accessibility_count=audit_summary.get('accessibility_count', 0),
            contrast_count=audit_summary.get('contrast_count', 0),
            dark_pattern_count=audit_summary.get('dark_pattern_count', 0)
        )
    
    def _query_llm(self, prompt: str) -> str:
        """Send query to LLM and return response.
        
        Args:
            prompt: Prompt text to send to LLM
            
        Returns:
            LLM response text
        """
        if not self._model:
            return ""
        
        try:
            # Add system instruction to the prompt
            full_prompt =  """
            You are an expert in web accessibility, inclusive design, and ethical UX.

            Role:
            - Identify barriers that prevent users from accessing or understanding content.
            - Recommend specific, actionable improvements to meet WCAG 2.1 guidelines.
            - Promote ethical and inclusive decision-making in product design.

            Expectations:
            - Reference WCAG criteria when applicable.
            - Use clear and direct language.
            - Avoid vague or generic advice.
            - Focus on practical steps that design and engineering teams can implement.

            Your output should:
            - Diagnose the issue concisely.
            - Explain why it matters for users.
            - Provide a clear, actionable fix.

            Goal:
            Help teams build accessible, inclusive, and ethical digital products that work for everyone.
        """ + prompt
            
            # Configure generation parameters
            generation_config = {
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
            
            response = self._model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            return response.text.strip()
            
        except Exception as e:
            return f"LLM Analysis Error: {str(e)}"
    
    def _query_llm_multimodal(self, content_parts: list) -> str:
        """Send multimodal query (text + images) to LLM.
        
        Args:
            content_parts: List of content parts (strings and PIL Images)
            
        Returns:
            LLM response text
        """
        if not self._model:
            return ""
        
        try:
            # Configure generation parameters
            generation_config = {
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
            
            response = self._model.generate_content(
                content_parts,
                generation_config=generation_config
            )
            
            return response.text.strip()
            
        except Exception as e:
            return f"Multimodal LLM Analysis Error: {str(e)}"

    def assess_design_multimodal(
        self,
        *,
        screenshot_path: Optional[str] = None,
        url: Optional[str] = None,
        dom_excerpt: Optional[str] = None,
        accessibility_summary: Optional[dict] = None,
        contrast_summary: Optional[dict] = None,
        dark_pattern_summary: Optional[dict] = None,
    ) -> Optional[dict]:
        """Use the LLM to validate contrast and dark-pattern findings."""

        if not self.is_available():
            return None

        heuristics_payload = {
            "accessibility": accessibility_summary or {},
            "contrast": contrast_summary or {},
            "dark_patterns": dark_pattern_summary or {},
            "url": url,
        }

        prompt = textwrap.dedent(
            """
            You are an independent UX fairness auditor. Review the provided website evidence
            (screenshot plus heuristics) and validate two things:

            1. Ethical UX / Potential Dark Patterns
               - Identify only genuine manipulative patterns.
               - Prefer precision over recall; ignore benign persuasive design.
               - For each confirmed pattern, provide label, severity (none/low/medium/high),
                 confidence (0.0-1.0) and an explanation users understand.
               - Suggest a clear recommendation to fix the pattern.
               - Compute an overall score in [0, 1] where 1.0 means no concerning patterns.

            2. Visual Contrast & Legibility
               - Focus on real text contrast or readability issues.
               - Ignore decorative elements or acceptable gradients.
               - For confirmed contrast issues, state area, severity (low/medium/high),
                 estimated contrast ratio if visible, and actionable recommendation.
               - Provide an overall score in [0, 1] where 1.0 means excellent contrast.

            Respond with strict JSON matching:

            {
              "dark_patterns": {
                "overall_score": float,
                "patterns": [
                  {
                    "label": string,
                    "severity": "none" | "low" | "medium" | "high",
                    "confidence": float,
                    "explanation": string,
                    "recommendation": string
                  }
                ]
              },
              "contrast": {
                "overall_score": float,
                "issues": [
                  {
                    "area": string,
                    "severity": "low" | "medium" | "high",
                    "contrast_ratio_estimate": float | null,
                    "explanation": string,
                    "recommendation": string
                  }
                ]
              }
            }

            Do not emit any text outside the JSON object.
            """
        )

        if dom_excerpt:
            truncated = dom_excerpt[:4000]
        else:
            truncated = ""

        prompt += "\nHeuristic signals (JSON):\n" + json.dumps(heuristics_payload, ensure_ascii=False) + "\n"
        if truncated:
            prompt += "\nDOM excerpt (truncated):\n" + truncated + "\n"

        content_parts = []

        if screenshot_path and os.path.exists(screenshot_path):
            try:
                from PIL import Image as PILImage

                image = PILImage.open(screenshot_path)
                content_parts.append(image)
            except Exception as exc:  # pragma: no cover - best effort context
                print(f"DEBUG LLM: Failed to load screenshot for multimodal check: {exc}")

        content_parts.append(prompt)

        generation_config = {
            "temperature": min(self.config.temperature, 0.3),
            "max_output_tokens": min(self.config.max_tokens, 4000),
        }

        try:
            response = self._model.generate_content(
                content_parts,
                generation_config=generation_config,
            )
            raw_text = (response.text or "").strip()
            return self._parse_json_response(raw_text)
        except Exception as exc:
            print(f"DEBUG LLM: Multimodal validation failed: {exc}")
            return None

    def _parse_json_response(self, raw_text: str) -> Optional[dict]:
        if not raw_text:
            return None

        cleaned = raw_text.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # Attempt to locate the first JSON object in the string
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    return None
            return None
