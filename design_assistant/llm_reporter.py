"""AI-powered report generation for detailed accessibility and UX insights.

This module generates comprehensive, narrative reports combining rule-based templates
with optional LLM integration (GPT-4o) for enhanced natural language analysis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .pipeline import PipelineResult

try:
    from .llm_integration import LLMAnalyzer, LLMConfig
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


@dataclass
class LLMReportSection:
    """Individual section of the AI-generated report."""
    
    title: str
    content: str
    severity: str  # "critical", "warning", "info"


class LLMReportGenerator:
    """Generates comprehensive, narrative reports combining rule-based templates
    with optional LLM analysis.
    
    When LLM is configured, merges GPT-4o insights with automated audit results
    for enhanced explanations and recommendations.
    """
    
    def __init__(self, llm_config: Optional["LLMConfig"] = None):
        """Initialize the report generator.
        
        Args:
            llm_config: Optional LLM configuration for enhanced analysis.
                       If None, uses rule-based templates only.
        """
        self.llm_config = llm_config
        self.llm_analyzer = None
        
        if llm_config and HAS_LLM:
            try:
                self.llm_analyzer = LLMAnalyzer(llm_config)
            except Exception as e:
                print(f"Warning: Could not initialize LLM analyzer: {e}")
                print("Falling back to rule-based reporting only.")
        
    def generate_comprehensive_report(self, result: "PipelineResult") -> str:
        """Generate a detailed narrative report from audit results.
        
        Args:
            result: Pipeline result containing all audit data
            
        Returns:
            Comprehensive markdown-formatted report
        """
        sections = []
        
        # Executive Summary
        sections.append(self._generate_executive_summary(result))
        
        # Accessibility Analysis
        if result.accessibility:
            sections.append(self._generate_accessibility_analysis(result))
        
        # Contrast & Visual Design
        sections.append(self._generate_contrast_analysis(result))
        
        # Dark Pattern & Ethics Analysis
        sections.append(self._generate_dark_pattern_analysis(result))
        
        # Recommendations
        sections.append(self._generate_recommendations(result))
        
        # Technical Details
        sections.append(self._generate_technical_details(result))
        
        return self._format_report(sections)
    
    def _generate_executive_summary(self, result: "PipelineResult") -> LLMReportSection:
        """Generate high-level executive summary."""
        fairness_score = result.fairness.value
        
        if fairness_score >= 0.8:
            assessment = "excellent"
            tone = "The interface demonstrates strong adherence to accessibility standards and ethical design principles."
        elif fairness_score >= 0.6:
            assessment = "good with room for improvement"
            tone = "The interface shows good baseline compliance but has opportunities for enhancement."
        elif fairness_score >= 0.4:
            assessment = "needs improvement"
            tone = "The interface has several accessibility and ethical concerns that should be addressed."
        else:
            assessment = "critical issues detected"
            tone = "The interface has significant accessibility barriers and ethical design issues requiring immediate attention."
        
        acc_score = f"{result.accessibility.score:.2%}" if result.accessibility else "N/A (screenshot-only mode)"
        acc_violations = len(result.accessibility.violations) if result.accessibility else 0
        
        content = f"""
## Executive Summary

**Overall Design Fairness Score: {fairness_score:.2f}/1.0** ({assessment})

{tone}

### Key Findings:
- **Accessibility Compliance**: {acc_score}
- **Visual Contrast**: {result.contrast.average_contrast:.2f}:1 average ratio
- **Ethical UX Score**: {result.dark_patterns.score:.2%}

### At a Glance:
- {acc_violations} accessibility violations detected
- {len(result.contrast.violations)} low-contrast regions identified
- {len(result.dark_patterns.flags)} potential dark patterns flagged

This report provides a comprehensive analysis of the interface's compliance with WCAG accessibility standards, 
visual design quality, and ethical user experience patterns.
"""
        return LLMReportSection(
            title="Executive Summary",
            content=content,
            severity="info"
        )
    
    def _generate_accessibility_analysis(self, result: "PipelineResult") -> LLMReportSection:
        """Generate detailed accessibility findings."""
        acc = result.accessibility
        if not acc:
            return LLMReportSection(
                title="Accessibility Analysis",
                content="N/A - Screenshot-only mode does not support full accessibility auditing.",
                severity="info"
            )
        
        severity = "critical" if acc.score < 0.5 else "warning" if acc.score < 0.8 else "info"
        
        violations_by_impact = {}
        for v in acc.violations:
            impact = v.impact or "unknown"
            violations_by_impact.setdefault(impact, []).append(v)
        
        # Get LLM analysis if available
        llm_insights = ""
        if self.llm_analyzer:
            try:
                # Prepare violation summary for LLM
                violations_data = [
                    {
                        "id": v.violation_id,
                        "impact": v.impact,
                        "description": v.description,
                        "node_count": len(v.nodes)
                    }
                    for v in acc.violations[:20]  # Top 20 violations
                ]
                llm_response = self.llm_analyzer.analyze_accessibility(
                    violations=violations_data,
                    score=acc.score
                )
                llm_insights = f"\n\n### AI-Powered Analysis\n\n{llm_response}\n"
            except Exception as e:
                print(f"Warning: LLM analysis failed: {e}")
        
        content = f"""
## Accessibility Analysis (WCAG Compliance)

**Score**: {acc.score:.2%} | **Total Violations**: {len(acc.violations)}

### Overview
{"This interface has critical accessibility barriers that prevent users with disabilities from accessing content." if acc.score < 0.5 else 
 "This interface has moderate accessibility issues that should be addressed to ensure inclusive design." if acc.score < 0.8 else
 "This interface demonstrates good accessibility practices with minor issues to resolve."}
{llm_insights}
### Violations Breakdown by Impact:
"""
        
        for impact in ["critical", "serious", "moderate", "minor"]:
            if impact in violations_by_impact:
                viols = violations_by_impact[impact]
                content += f"\n#### {impact.title()} Impact ({len(viols)} issues)\n"
                
                # Group by violation ID
                by_id = {}
                for v in viols:
                    by_id.setdefault(v.violation_id, []).append(v)
                
                for vid, instances in list(by_id.items())[:5]:  # Top 5
                    v = instances[0]
                    content += f"\n**{vid}** ({len(instances)} instance{'s' if len(instances) > 1 else ''})\n"
                    content += f"- Description: {v.description}\n"
                    if v.help_url:
                        content += f"- Learn more: {v.help_url}\n"
                    content += f"- Affected elements: {min(len(instances), 3)} shown\n"
                    for node in v.nodes[:3]:
                        content += f"  - `{node[:100]}...`\n" if len(node) > 100 else f"  - `{node}`\n"
        
        content += """

### Impact on Users
These accessibility violations may prevent or hinder users with:
- Visual impairments (screen reader users, low vision)
- Motor disabilities (keyboard-only navigation)
- Cognitive disabilities (complex navigation, unclear labels)
- Temporary disabilities (broken mouse, bright sunlight)
"""
        
        return LLMReportSection(
            title="Accessibility Analysis",
            content=content,
            severity=severity
        )
    
    def _generate_contrast_analysis(self, result: "PipelineResult") -> LLMReportSection:
        """Generate contrast and visual design analysis."""
        contrast = result.contrast
        avg_contrast = contrast.average_contrast
        violations = len(contrast.violations)
        
        severity = "critical" if avg_contrast < 3.0 else "warning" if avg_contrast < 4.5 else "info"
        
        # Get LLM analysis if available
        llm_insights = ""
        if self.llm_analyzer:
            try:
                violations_data = [
                    {
                        "bbox": v.bbox,
                        "ratio": v.contrast_ratio
                    }
                    for v in contrast.violations[:15]  # Top 15 violations
                ]
                llm_response = self.llm_analyzer.analyze_contrast(
                    violations=violations_data,
                    avg_contrast=avg_contrast
                )
                llm_insights = f"\n\n### AI-Powered Analysis\n\n{llm_response}\n"
            except Exception as e:
                print(f"Warning: LLM analysis failed: {e}")
        
        content = f"""
## Visual Contrast Analysis

**Average Contrast Ratio**: {avg_contrast:.2f}:1 | **Low-Contrast Regions**: {violations}

### WCAG Standards
- **AA Standard (Normal Text)**: 4.5:1 minimum
- **AA Standard (Large Text)**: 3:1 minimum
- **AAA Standard (Normal Text)**: 7:1 minimum

### Assessment
{"🔴 CRITICAL: The interface has significant contrast issues that make text illegible for users with low vision or color blindness." if avg_contrast < 3.0 else
 "⚠️ WARNING: Multiple regions fall below WCAG AA standards. Users with visual impairments may struggle to read content." if avg_contrast < 4.5 else
 "✅ GOOD: Most text meets minimum contrast requirements, though some areas could be improved for AAA compliance."}
{llm_insights}
### Detected Issues
"""
        
        if violations > 0:
            content += f"\nFound {violations} regions with insufficient contrast:\n\n"
            for i, v in enumerate(contrast.violations[:10], 1):
                x, y, w, h = v.bbox
                content += f"{i}. **Region at ({x}, {y})** - Size: {w}×{h}px - Ratio: {v.contrast_ratio:.2f}:1\n"
            
            if violations > 10:
                content += f"\n*...and {violations - 10} more violations*\n"
        else:
            content += "\nNo significant contrast violations detected. The interface maintains readable text throughout.\n"
        
        content += """

### User Impact
Low contrast affects:
- Users with low vision or color blindness
- Users in bright sunlight or poor lighting
- Older users with age-related vision changes
- All users experiencing screen glare

### Recommendations
- Increase foreground/background color difference
- Use darker text on light backgrounds (or vice versa)
- Test with color blindness simulators
- Avoid relying solely on color to convey information
"""
        
        return LLMReportSection(
            title="Contrast Analysis",
            content=content,
            severity=severity
        )
    
    def _generate_dark_pattern_analysis(self, result: "PipelineResult") -> LLMReportSection:
        """Generate ethical UX and dark pattern analysis."""
        dp = result.dark_patterns
        flags = len(dp.flags)
        
        severity = "critical" if dp.score < 0.5 else "warning" if dp.score < 0.8 else "info"
        
        # Get LLM analysis if available
        llm_insights = ""
        if self.llm_analyzer:
            try:
                flags_data = [
                    {
                        "label": f.label,
                        "text": f.text[:200],  # Truncate long text
                        "score": f.score
                    }
                    for f in dp.flags[:15]  # Top 15 flags
                ]
                llm_response = self.llm_analyzer.analyze_dark_patterns(
                    flags=flags_data,
                    score=dp.score
                )
                llm_insights = f"\n\n### AI-Powered Ethical Assessment\n\n{llm_response}\n"
            except Exception as e:
                print(f"Warning: LLM analysis failed: {e}")
        
        content = f"""
## Ethical UX & Dark Pattern Analysis

**Ethical UX Score**: {dp.score:.2%} | **Potential Dark Patterns**: {flags}

### What Are Dark Patterns?
Dark patterns are deceptive design techniques that manipulate users into taking actions they didn't intend, 
such as subscribing to services, sharing personal data, or making purchases.

### Assessment
{"🔴 CRITICAL: Multiple manipulative design patterns detected. The interface may violate user trust and consent principles." if dp.score < 0.5 else
 "⚠️ WARNING: Some potentially manipulative design elements identified. Review for ethical compliance." if dp.score < 0.8 else
 "✅ GOOD: The interface demonstrates ethical design practices with minimal concerning patterns."}
{llm_insights}
"""
        
        if flags > 0:
            content += "### Detected Patterns\n\n"
            
            by_label = {}
            for flag in dp.flags:
                by_label.setdefault(flag.label, []).append(flag)
            
            for label, instances in by_label.items():
                content += f"#### {label} ({len(instances)} instance{'s' if len(instances) > 1 else ''})\n\n"
                
                # Explain the pattern
                explanations = {
                    "Urgency": "Creates artificial time pressure to rush user decisions",
                    "Confirm-shaming": "Uses guilt or shame to manipulate user choices",
                    "Misdirection": "Directs attention away from important information or choices",
                }
                content += f"*{explanations.get(label, 'Manipulative design element')}*\n\n"
                
                for i, flag in enumerate(instances[:5], 1):
                    content += f"{i}. **Confidence: {flag.score:.0%}**\n"
                    content += f"   - Text: \"{flag.text[:150]}{'...' if len(flag.text) > 150 else ''}\"\n\n"
                
                if len(instances) > 5:
                    content += f"*...and {len(instances) - 5} more instances*\n\n"
        else:
            content += "### No Dark Patterns Detected\n\nThe interface text does not contain obvious manipulative language patterns.\n"
        
        content += """

### Ethical Design Principles
A trustworthy interface should:
- Respect user autonomy and informed consent
- Be transparent about costs, commitments, and data usage
- Make it easy to cancel, unsubscribe, or delete accounts
- Avoid pressuring users with artificial urgency
- Present choices clearly without guilt or shame
"""
        
        return LLMReportSection(
            title="Dark Pattern Analysis",
            content=content,
            severity=severity
        )
    
    def _generate_recommendations(self, result: "PipelineResult") -> LLMReportSection:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Accessibility recommendations
        if result.accessibility and result.accessibility.score < 0.8:
            recommendations.append({
                "priority": "HIGH",
                "area": "Accessibility",
                "action": "Address WCAG violations, focusing on critical and serious issues first",
                "impact": "Enables access for users with disabilities, reduces legal risk"
            })
        
        # Contrast recommendations
        if result.contrast.average_contrast < 4.5:
            recommendations.append({
                "priority": "HIGH",
                "area": "Visual Design",
                "action": "Improve text contrast to meet WCAG AA standards (4.5:1 minimum)",
                "impact": "Makes content readable for users with low vision and in various lighting conditions"
            })
        
        # Dark pattern recommendations
        if result.dark_patterns.score < 0.8:
            recommendations.append({
                "priority": "MEDIUM",
                "area": "Ethical UX",
                "action": "Remove or rephrase manipulative language and design elements",
                "impact": "Builds user trust, improves brand reputation, ensures ethical compliance"
            })
        
        # Always add testing recommendation
        recommendations.append({
            "priority": "MEDIUM",
            "area": "User Testing",
            "action": "Conduct usability testing with diverse users including those with disabilities",
            "impact": "Validates fixes and uncovers issues not caught by automated tools"
        })
        
        # Get LLM recommendations if available
        llm_recommendations = ""
        if self.llm_analyzer:
            try:
                audit_summary = {
                    "accessibility_score": result.accessibility.score if result.accessibility else None,
                    "accessibility_violations": len(result.accessibility.violations) if result.accessibility else 0,
                    "contrast_avg": result.contrast.average_contrast,
                    "contrast_violations": len(result.contrast.violations),
                    "dark_patterns_score": result.dark_patterns.score,
                    "dark_patterns_count": len(result.dark_patterns.flags),
                    "fairness_score": result.fairness.value
                }
                llm_response = self.llm_analyzer.generate_recommendations(audit_summary)
                llm_recommendations = f"\n\n### AI-Powered Recommendations\n\n{llm_response}\n"
            except Exception as e:
                print(f"Warning: LLM recommendations failed: {e}")
        
        content = "## Actionable Recommendations\n\n"
        
        # Add LLM recommendations first if available
        if llm_recommendations:
            content += llm_recommendations
            content += "\n### Rule-Based Recommendations\n\n"
        
        for i, rec in enumerate(recommendations, 1):
            content += f"### {i}. [{rec['priority']}] {rec['area']}\n\n"
            content += f"**Action**: {rec['action']}\n\n"
            content += f"**Impact**: {rec['impact']}\n\n"
        
        content += """
### Implementation Strategy

1. **Quick Wins (1-2 weeks)**
   - Fix critical accessibility violations
   - Adjust color contrast for key text elements
   - Remove obvious dark pattern language

2. **Medium Term (1-2 months)**
   - Comprehensive WCAG audit and remediation
   - Redesign low-contrast UI components
   - Establish ethical design guidelines

3. **Long Term (Ongoing)**
   - Regular accessibility audits
   - User testing with diverse populations
   - Continuous monitoring of design patterns
"""
        
        return LLMReportSection(
            title="Recommendations",
            content=content,
            severity="info"
        )
    
    def _generate_technical_details(self, result: "PipelineResult") -> LLMReportSection:
        """Generate technical audit details."""
        content = f"""
## Technical Audit Details

### Scoring Methodology

**Design Fairness Score** = α × Accessibility + β × Ethical UX

- α (Accessibility weight): {result.fairness.alpha}
- β (Ethical UX weight): {result.fairness.beta}
- Final Score: {result.fairness.value:.3f}

### Component Scores

"""
        
        if result.accessibility:
            content += f"""
| Component | Score | Weight | Contribution |
|-----------|-------|--------|--------------|
| Accessibility | {result.accessibility.score:.3f} | {result.fairness.alpha} | {(result.accessibility.score * result.fairness.alpha):.3f} |
| Ethical UX | {result.dark_patterns.score:.3f} | {result.fairness.beta} | {(result.dark_patterns.score * result.fairness.beta):.3f} |
"""
        else:
            content += f"""
| Component | Score | Weight | Contribution |
|-----------|-------|--------|--------------|
| Accessibility | N/A | {result.fairness.alpha} | N/A |
| Ethical UX | {result.dark_patterns.score:.3f} | {result.fairness.beta} | {(result.dark_patterns.score * result.fairness.beta):.3f} |
"""
        
        content += f"""

### Audit Artifacts

- **Screenshot**: `{result.artifacts.get('screenshot_path', 'N/A')}`
- **DOM HTML**: `{result.artifacts.get('dom_path', 'N/A')}`
- **Axe Report**: `{result.artifacts.get('axe_json_path', 'N/A')}`

### Tools Used

- **Accessibility**: axe-core via Selenium
- **Contrast Detection**: OpenCV with WCAG luminance calculations
- **Dark Patterns**: {"Transformer NLP model" if result.dark_patterns.raw_outputs else "Keyword heuristics"}
- **Reporting**: AI-powered analysis with contextual insights

### Limitations

- Automated tools catch ~30-40% of accessibility issues; manual testing required
- Contrast detection uses heuristics; manual review of flagged regions recommended
- Dark pattern detection based on text analysis; visual deception not captured
- Screenshot-only mode cannot perform full accessibility audits
"""
        
        return LLMReportSection(
            title="Technical Details",
            content=content,
            severity="info"
        )
    
    def _format_report(self, sections: list[LLMReportSection]) -> str:
        """Format all sections into final report."""
        report = "# Comprehensive Design Fairness Audit Report\n\n"
        report += f"*Generated by AI-Powered Design Assistant*\n\n"
        report += "---\n\n"
        
        for section in sections:
            report += section.content + "\n\n---\n\n"
        
        report += """
## About This Report

This comprehensive audit was generated using AI-powered analysis tools that combine:
- Automated accessibility testing (axe-core)
- Computer vision for contrast analysis (OpenCV)
- Natural language processing for dark pattern detection (Transformers)
- Intelligent report generation using contextual templates and rule-based analysis

**Note**: The narrative explanations are generated using intelligent templates based on audit results. 
Future versions may integrate large language models (GPT, Claude, etc.) for more natural language generation.

For questions or to request a manual accessibility audit, please consult with accessibility experts.
"""
        
        return report
