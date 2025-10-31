"""High-level orchestration logic for the AI-powered design assistant."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

from .audits.accessibility import AccessibilityAuditor, AccessibilityReport
from .audits.contrast import ContrastAuditor, ContrastReport
from .audits.dark_patterns import DarkPatternAuditor, DarkPatternReport
from .collectors.selenium_collector import SeleniumCollector, SeleniumArtifacts
from .collectors.screenshot_loader import ScreenshotLoader
from .fusion import DesignFairnessScore
from .reporting import PDFReportWriter, JSONReportWriter, MarkdownReportWriter

if TYPE_CHECKING:
    try:
        from .llm_integration import LLMConfig
    except ImportError:
        LLMConfig = None


class InputMode(str, Enum):
    """Enumerates supported input modalities."""

    URL = "url"
    SCREENSHOT = "screenshot"


@dataclass
class PipelineResult:
    """Aggregated audit outputs and scoring metadata."""

    accessibility: Optional[AccessibilityReport]
    contrast: ContrastReport
    dark_patterns: DarkPatternReport
    fairness: DesignFairnessScore
    artifacts: Dict[str, Any]

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "fairness": self.fairness.to_dict(),
            "accessibility": self.accessibility.to_dict() if self.accessibility else None,
            "contrast": self.contrast.to_dict(),
            "dark_patterns": self.dark_patterns.to_dict(),
            "artifacts": {
                key: str(value) if isinstance(value, Path) else value
                for key, value in self.artifacts.items()
            },
        }


class DesignAssistant:
    """Coordinates collectors, audits, and report generation."""

    def __init__(
        self,
        selenium_collector: Optional[SeleniumCollector] = None,
        accessibility_auditor: Optional[AccessibilityAuditor] = None,
        contrast_auditor: Optional[ContrastAuditor] = None,
        dark_pattern_auditor: Optional[DarkPatternAuditor] = None,
        pdf_writer: Optional[PDFReportWriter] = None,
        json_writer: Optional[JSONReportWriter] = None,
        markdown_writer: Optional[MarkdownReportWriter] = None,
        llm_config: Optional[Any] = None,
        alpha: float = 0.5,
        beta: float = 0.5,
    ) -> None:
        self.selenium_collector = selenium_collector or SeleniumCollector()
        self.accessibility_auditor = accessibility_auditor or AccessibilityAuditor()
        self.contrast_auditor = contrast_auditor or ContrastAuditor()
        self.dark_pattern_auditor = dark_pattern_auditor or DarkPatternAuditor()
        self.llm_config = llm_config
        
        # Initialize report writers with LLM config
        # Important: Pass llm_config when creating default writers
        if pdf_writer is None:
            self.pdf_writer = PDFReportWriter(llm_config=llm_config)
        else:
            self.pdf_writer = pdf_writer
            
        self.json_writer = json_writer or JSONReportWriter()
        
        if markdown_writer is None:
            self.markdown_writer = MarkdownReportWriter(llm_config=llm_config)
        else:
            self.markdown_writer = markdown_writer
            
        self.alpha = alpha
        self.beta = beta

    def run(self, mode: InputMode, value: str, *, output_dir: Optional[Path] = None) -> PipelineResult:
        """Execute the design assistant pipeline for the provided input."""

        output_dir = output_dir or Path("outputs")
        output_dir.mkdir(parents=True, exist_ok=True)

        if mode is InputMode.URL:
            selenium_artifacts = self._collect_from_url(value, output_dir)
            screenshot = selenium_artifacts.screenshot
            dom_text = selenium_artifacts.visible_text
            accessibility_report = selenium_artifacts.accessibility
        elif mode is InputMode.SCREENSHOT:
            selenium_artifacts = None
            screenshot_loader = ScreenshotLoader()
            screenshot = screenshot_loader.load_from_path(value)
            dom_text = ""
            accessibility_report = None
        else:
            raise ValueError(f"Unsupported input mode: {mode}")

        contrast_report = self.contrast_auditor.audit(screenshot.image)
        dark_pattern_report = self.dark_pattern_auditor.audit(dom_text)
        fairness_score = DesignFairnessScore.from_components(
            accessibility_score=accessibility_report.score if accessibility_report else None,
            ethical_score=dark_pattern_report.score,
            alpha=self.alpha,
            beta=self.beta,
        )

        artifacts: Dict[str, Any] = {
            "screenshot_path": screenshot.path,
            "dom_text": dom_text[:1000],  # avoid bloating serialized results
        }
        if selenium_artifacts:
            artifacts.update(
                {
                    "url": selenium_artifacts.url,
                    "dom_path": selenium_artifacts.dom_path,
                    "axe_json_path": selenium_artifacts.axe_json_path,
                }
            )

        result = PipelineResult(
            accessibility=accessibility_report,
            contrast=contrast_report,
            dark_patterns=dark_pattern_report,
            fairness=fairness_score,
            artifacts=artifacts,
        )

        self.json_writer.write(result, output_dir / "audit.json")
        self.pdf_writer.write(result, output_dir / "audit.pdf")
        self.markdown_writer.write(result, output_dir / "audit_report.md")

        return result

    def _collect_from_url(self, url: str, output_dir: Path) -> SeleniumArtifacts:
        collector_result = self.selenium_collector.collect(url, output_dir=output_dir)
        if collector_result.accessibility is None and collector_result.axe_results is not None:
            collector_result = replace(
                collector_result,
                accessibility=self.accessibility_auditor.audit_from_raw(
                    collector_result.axe_results
                ),
            )
        return collector_result
