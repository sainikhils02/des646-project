"""High-level orchestration logic for the AI-powered design assistant."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

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

    def _save_analysis_images(self, screenshot, contrast_report, output_dir: Path) -> List[str]:
        """Save analysis images for PDF reports."""
        analysis_images = []
        
        try:
            # 1. Save original screenshot copy for PDF
            original_screenshot_path = output_dir / "original_screenshot.png"
            if hasattr(screenshot, 'image') and screenshot.image:
                screenshot.image.save(original_screenshot_path)
                analysis_images.append(str(original_screenshot_path))
            
            # 2. Save contrast analysis visualization if available
            if hasattr(contrast_report, 'violations') and contrast_report.violations:
                contrast_img_path = output_dir / "contrast_analysis.png"
                self._create_contrast_visualization(contrast_report, screenshot, str(contrast_img_path))
                analysis_images.append(str(contrast_img_path))
            
            # 3. Save accessibility summary image if accessibility data exists
            if hasattr(self, 'accessibility_report') and self.accessibility_report:
                accessibility_img_path = output_dir / "accessibility_summary.png"
                self._create_accessibility_visualization(self.accessibility_report, str(accessibility_img_path))
                analysis_images.append(str(accessibility_img_path))
                
        except Exception as e:
            print(f"Warning: Could not save analysis images: {e}")
        
        return analysis_images

    def _create_contrast_visualization(self, contrast_report, screenshot, output_path: str):
        """Create a visualization showing contrast violations."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import matplotlib.pyplot as plt
            
            # Create a simple visualization
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Plot contrast violations if any
            if hasattr(contrast_report, 'violations') and contrast_report.violations:
                violation_counts = {}
                for violation in contrast_report.violations:
                    violation_type = getattr(violation, 'violation_type', 'Unknown')
                    violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1
                
                # Create bar chart
                ax.bar(violation_counts.keys(), violation_counts.values(), color='red', alpha=0.7)
                ax.set_title('Contrast Violations by Type')
                ax.set_ylabel('Number of Violations')
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                # Save the plot
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
            else:
                # Create a "No violations" image
                fig, ax = plt.subplots(figsize=(8, 2))
                ax.text(0.5, 0.5, '✅ No Contrast Violations Found', 
                    ha='center', va='center', fontsize=16, color='green')
                ax.axis('off')
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                
        except Exception as e:
            print(f"Could not create contrast visualization: {e}")
            # Create a simple placeholder image
            self._create_placeholder_image(output_path, "Contrast Analysis")

    def _create_accessibility_visualization(self, accessibility_report, output_path: str):
        """Create a visualization for accessibility findings."""
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if hasattr(accessibility_report, 'violations') and accessibility_report.violations:
                violation_severity = {}
                for violation in accessibility_report.violations:
                    severity = getattr(violation, 'impact', 'unknown')
                    violation_severity[severity] = violation_severity.get(severity, 0) + 1
                
                # Create pie chart
                colors = ['red', 'orange', 'yellow', 'green']
                ax.pie(violation_severity.values(), labels=violation_severity.keys(), 
                    autopct='%1.1f%%', colors=colors[:len(violation_severity)])
                ax.set_title('Accessibility Issues by Severity')
                
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
            else:
                # Create a "No violations" image
                fig, ax = plt.subplots(figsize=(8, 2))
                ax.text(0.5, 0.5, '✅ No Accessibility Issues Found', 
                    ha='center', va='center', fontsize=16, color='green')
                ax.axis('off')
                plt.savefig(output_path, dpi=150, bbox_inches='tight')
                plt.close()
                
        except Exception as e:
            print(f"Could not create accessibility visualization: {e}")
            self._create_placeholder_image(output_path, "Accessibility Analysis")

    def _create_placeholder_image(self, output_path: str, title: str):
        """Create a placeholder image when analysis fails."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import numpy as np
            
            # Create a simple placeholder image
            img = Image.new('RGB', (400, 200), color='lightgray')
            draw = ImageDraw.Draw(img)
            
            # Add title text
            try:
                font = ImageFont.load_default()
                text_bbox = draw.textbbox((0, 0), title, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                x = (400 - text_width) // 2
                y = (200 - text_height) // 2
                draw.text((x, y), title, fill='black', font=font)
            except:
                draw.text((150, 90), title, fill='black')
            
            img.save(output_path)
        except Exception as e:
            print(f"Could not create placeholder image: {e}")
    
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

        # Save analysis images for PDF reports
        analysis_images = self._save_analysis_images(
            screenshot=screenshot,
            contrast_report=contrast_report,
            output_dir=output_dir
        )

        artifacts: Dict[str, Any] = {
            "screenshot_path": screenshot.path,
            "dom_text": dom_text[:1000],  # avoid bloating serialized results
            "analysis_images": analysis_images,  # Add analysis images to artifacts
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
