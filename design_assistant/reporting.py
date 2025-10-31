"""Report generation utilities (PDF, JSON, and Markdown)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
except ImportError:  # pragma: no cover - optional dependency
    A4 = None
    SimpleDocTemplate = None

if TYPE_CHECKING:  # pragma: no cover
    from .pipeline import PipelineResult

from .llm_reporter import LLMReportGenerator


@dataclass
class JSONReportWriter:
    """Writes pipeline results to a JSON artifact."""

    indent: int = 2

    def write(self, result: "PipelineResult", path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_json_dict(), indent=self.indent), encoding="utf-8")
        return path


@dataclass
class MarkdownReportWriter:
    """Writes a comprehensive LLM-powered markdown report."""
    
    llm_config: Optional[object] = None

    def write(self, result: "PipelineResult", path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        generator = LLMReportGenerator(llm_config=self.llm_config)
        report_content = generator.generate_comprehensive_report(result)
        path.write_text(report_content, encoding="utf-8")
        return path


@dataclass
class PDFReportWriter:
    """Writes a comprehensive PDF report using the LLM generator."""

    title: str = "Comprehensive Design Fairness Audit Report"
    llm_config: Optional[object] = None

    def write(self, result: "PipelineResult", path: Path) -> Optional[Path]:
        if SimpleDocTemplate is None:
            return None

        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate comprehensive markdown report first
        generator = LLMReportGenerator(llm_config=self.llm_config)
        markdown_content = generator.generate_comprehensive_report(result)
        
        # Convert markdown to PDF-friendly format
        doc = SimpleDocTemplate(str(path), pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        
        # Process markdown content into PDF elements
        lines = markdown_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                elements.append(Spacer(1, 6))
                continue
            
            # Headers
            if line.startswith('# '):
                elements.append(Paragraph(line[2:], styles["Title"]))
                elements.append(Spacer(1, 12))
            elif line.startswith('## '):
                elements.append(Paragraph(line[3:], styles["Heading1"]))
                elements.append(Spacer(1, 10))
            elif line.startswith('### '):
                elements.append(Paragraph(line[4:], styles["Heading2"]))
                elements.append(Spacer(1, 8))
            elif line.startswith('#### '):
                elements.append(Paragraph(line[5:], styles["Heading3"]))
                elements.append(Spacer(1, 6))
            # Bold text
            elif line.startswith('**') and line.endswith('**'):
                clean_line = line.replace('**', '<b>').replace('**', '</b>')
                elements.append(Paragraph(clean_line, styles["Normal"]))
            # Bullet points
            elif line.startswith('- ') or line.startswith('* '):
                clean_line = '• ' + line[2:]
                clean_line = self._convert_markdown_to_html(clean_line)
                elements.append(Paragraph(clean_line, styles["Normal"]))
                elements.append(Spacer(1, 3))
            # Numbered lists
            elif line and line[0].isdigit() and '. ' in line:
                clean_line = self._convert_markdown_to_html(line)
                elements.append(Paragraph(clean_line, styles["Normal"]))
                elements.append(Spacer(1, 3))
            # Horizontal rules
            elif line.startswith('---'):
                elements.append(Spacer(1, 12))
            # Regular paragraphs
            elif not line.startswith('|'):  # Skip table rows for now
                clean_line = self._convert_markdown_to_html(line)
                if clean_line:
                    elements.append(Paragraph(clean_line, styles["Normal"]))
                    elements.append(Spacer(1, 6))
        
        try:
            doc.build(elements)
            return path
        except Exception:
            # Fallback to simple summary if PDF generation fails
            return self._write_simple_summary(result, path)
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert markdown formatting to proper HTML tags for ReportLab."""
        # Escape ampersands
        text = text.replace('&', '&amp;')
        
        # Replace ** with bold tags
        parts = text.split('**')
        result = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are bold
                result.append(f'<b>{part}</b>')
            else:
                result.append(part)
        text = ''.join(result)
        
        # Strip any remaining single asterisks (italic markers we won't use)
        text = text.replace('*', '')
        
        # Escape any angle brackets that aren't our tags
        text = text.replace('<', '&lt;').replace('>', '&gt;')
        text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
        
        return text
    
    def _write_simple_summary(self, result: "PipelineResult", path: Path) -> Path:
        """Fallback simple summary if comprehensive PDF fails."""
        doc = SimpleDocTemplate(str(path), pagesize=A4)
        styles = getSampleStyleSheet()
        elements = [Paragraph(self.title, styles["Title"]), Spacer(1, 12)]

        fairness = result.fairness.to_dict()
        fairness_text = "<br/>".join(
            f"<b>{key}</b>: {value}" for key, value in fairness.items()
        )
        elements.append(Paragraph(fairness_text, styles["Normal"]))
        elements.append(Spacer(1, 12))

        if result.accessibility:
            accessibility_text = "<br/>".join(
                [
                    f"<b>Accessibility Score</b>: {result.accessibility.score}",
                    f"<b>Violations</b>: {len(result.accessibility.violations)}",
                ]
            )
            elements.append(Paragraph(accessibility_text, styles["Normal"]))
            elements.append(Spacer(1, 12))

        contrast_details = "<br/>".join(
            [
                f"<b>Average Contrast</b>: {result.contrast.average_contrast:.2f}",
                f"<b>Violations</b>: {len(result.contrast.violations)}",
            ]
        )
        elements.append(Paragraph(contrast_details, styles["Normal"]))
        elements.append(Spacer(1, 12))

        dark_pattern_text = "<br/>".join(
            [
                f"<b>Ethical UX Score</b>: {result.dark_patterns.score:.2f}",
                f"<b>Flagged Segments</b>: {len(result.dark_patterns.flags)}",
            ]
        )
        elements.append(Paragraph(dark_pattern_text, styles["Normal"]))

        doc.build(elements)
        return path
