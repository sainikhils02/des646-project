"""LLM integration for enhanced report generation using Google Gemini 2.0 Flash."""
from __future__ import annotations

import os
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
    model: str = "gemini-2.0-flash-exp"
    temperature: float = 0.7
    max_tokens: int = 4000
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
        
        if genai is not None and self.config.api_key:
            genai.configure(api_key=self.config.api_key)
            self._model = genai.GenerativeModel(self.config.model)
    
    def is_available(self) -> bool:
        """Check if LLM is available for use."""
        return self._model is not None
    
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
You are an accessibility expert conducting a WCAG audit. Analyze the following accessibility violations and provide:

1. A brief executive summary of the accessibility state
2. The top 3 most critical issues and their impact on users
3. Specific, actionable recommendations for fixing these issues
4. Explanation of which user groups are most affected

Accessibility Score: {score:.2%}
Number of Violations: {count}

Top Violations:
{violations_text}

Provide a professional, empathetic analysis focused on improving user experience for people with disabilities.
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
You are a visual design expert analyzing contrast compliance. Review these findings:

Average Contrast Ratio: {avg_contrast:.2f}:1
WCAG AA Requirement: 4.5:1 for normal text, 3:1 for large text
Number of Low-Contrast Regions: {count}

Sample Violations:
{violations_text}

Provide:
1. Assessment of overall visual readability
2. Impact on users with visual impairments
3. Specific color palette recommendations
4. Priority areas to fix first

Keep recommendations practical and design-friendly.
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
You are a UX ethics expert analyzing potentially manipulative design patterns.

Ethical UX Score: {score:.2%}
Flagged Patterns: {count}

Detected Patterns:
{patterns_text}

Provide:
1. Assessment of the ethical concerns present
2. Explanation of how these patterns manipulate user behavior
3. Recommendations for more ethical alternatives
4. Discussion of trust and brand reputation implications

Be constructive and focus on building user trust.
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
You are a product design consultant providing strategic recommendations based on this audit:

Overall Design Fairness Score: {fairness_score:.2f}/1.0
Accessibility Score: {accessibility_score}
Average Contrast: {contrast_ratio:.2f}:1
Ethical UX Score: {ethics_score:.2%}

Key Issues:
- {accessibility_count} accessibility violations
- {contrast_count} contrast issues
- {dark_pattern_count} potential dark patterns

Provide:
1. A prioritized action plan (Quick Wins, Medium-term, Long-term)
2. Resource allocation suggestions
3. Implementation timeline estimate
4. Success metrics to track improvements
5. Team roles needed (designers, developers, accessibility specialists)

Focus on practical, achievable steps that deliver real impact.
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
            full_prompt = """You are an expert in web accessibility, inclusive design, and ethical UX. 
Provide clear, actionable insights that help teams build better, more accessible products.

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
