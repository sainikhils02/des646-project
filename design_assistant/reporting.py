"""Report generation utilities (PDF, JSON, and Markdown)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Optional

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
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
    _image_pattern = re.compile(r"!\[(?P<alt>.*?)\]\((?P<src>.*?)\)")

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
        embedded_images: set[Path] = set()

        # Process markdown content into PDF elements
        lines = markdown_content.split('\n')
        table_buffer: list[str] = []

        for raw_line in lines:
            line = raw_line.strip()

            if table_buffer and not line.startswith('|'):
                elements.extend(self._build_table_elements(table_buffer, styles, doc.width))
                table_buffer = []

            if not line:
                elements.append(Spacer(1, 6))
                continue

            image_matches = self._extract_markdown_images(line)
            if image_matches:
                for alt, src in image_matches:
                    resolved = self._resolve_asset_path(src, path)
                    if resolved:
                        elements.extend(self._create_image_flowables(resolved, doc.width, alt, styles))
                        embedded_images.add(resolved)
                line = self._remove_markdown_images(line)
                if not line:
                    continue

            if line.startswith('|'):
                table_buffer.append(raw_line)
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
                clean_line = self._convert_markdown_to_html(line)
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
            else:
                clean_line = self._convert_markdown_to_html(line)
                if clean_line:
                    elements.append(Paragraph(clean_line, styles["Normal"]))
                    elements.append(Spacer(1, 6))

        if table_buffer:
            elements.extend(self._build_table_elements(table_buffer, styles, doc.width))

        self._append_analysis_images(result, elements, doc, styles, path, embedded_images)
        
        try:
            doc.build(elements)
            return path
        except Exception as e:
            # Log the error with details
            print(f"PDF generation error: {e}")
            print(f"Error type: {type(e).__name__}")
            # Fallback to simple summary if PDF generation fails
            return self._write_simple_summary(result, path)
    
    def _convert_markdown_to_html(self, text: str) -> str:
        """Convert markdown formatting to proper HTML tags for ReportLab."""
        # Replace ** with bold tags using simple split approach
        parts = text.split('**')
        result = []
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Odd indices are bold text
                # Escape XML special characters in bold content
                part = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                result.append(f'<b>{part}</b>')
            else:
                # Escape XML special characters in regular content
                part = part.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                result.append(part)
        text = ''.join(result)
        
        # Strip any remaining single asterisks (we don't handle italics)
        text = text.replace('*', '')
        
        return text

    def _extract_markdown_images(self, line: str):
        return self._image_pattern.findall(line)

    def _remove_markdown_images(self, line: str) -> str:
        return self._image_pattern.sub('', line).strip()

    @staticmethod
    def _is_separator_cell(cell: str) -> bool:
        stripped = cell.strip()
        return bool(stripped) and set(stripped) <= {':', '-'}

    def _build_table_elements(self, table_lines: list[str], styles, doc_width: float):
        rows = []
        for raw in table_lines:
            cleaned = raw.strip()
            if not cleaned:
                continue
            cleaned = cleaned.strip('|')
            cells = [cell.strip() for cell in cleaned.split('|')]
            rows.append(cells)

        if not rows:
            return []

        header = None
        data_rows = rows
        if len(rows) >= 2 and all(self._is_separator_cell(cell) for cell in rows[1]):
            header = rows[0]
            data_rows = rows[2:]

        processed_rows = []
        if header:
            processed_rows.append([
                Paragraph(self._convert_markdown_to_html(cell), styles["Heading4"])
                for cell in header
            ])

        body_style = styles["BodyText"]
        for row in data_rows:
            processed_rows.append([
                Paragraph(self._convert_markdown_to_html(cell), body_style)
                for cell in row
            ])

        num_cols = max(len(row) for row in processed_rows) if processed_rows else 0
        col_widths = [doc_width / num_cols] * num_cols if num_cols else None

        table = Table(processed_rows, colWidths=col_widths, hAlign='LEFT')
        style_commands = [
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]
        if header:
            style_commands.extend([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ])

        table.setStyle(TableStyle(style_commands))
        return [table, Spacer(1, 6)]

    def _resolve_asset_path(self, asset: str, report_path: Path) -> Optional[Path]:
        if not asset or asset.startswith('http'):
            return None

        candidates = []
        candidate_path = Path(asset)
        if candidate_path.is_absolute():
            candidates.append(candidate_path)
        else:
            candidates.extend([
                report_path.parent / candidate_path,
                Path('outputs') / candidate_path,
                candidate_path,
            ])

        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except Exception:
                resolved = candidate
            if resolved.exists():
                return resolved
        return None

    def _create_image_flowables(self, image_path: Path, doc_width: float, alt_text: Optional[str], styles):
        flowables = []
        try:
            img = Image(str(image_path))
            if doc_width and img.drawWidth > doc_width:
                scale = doc_width / float(img.drawWidth)
                img.drawWidth = doc_width
                img.drawHeight = img.drawHeight * scale
            flowables.append(img)
            flowables.append(Spacer(1, 4))
            if alt_text:
                caption_html = f"<i>{self._convert_markdown_to_html(alt_text)}</i>"
                flowables.append(Paragraph(caption_html, styles["BodyText"]))
                flowables.append(Spacer(1, 6))
            else:
                flowables.append(Spacer(1, 8))
        except Exception as exc:
            print(f"PDF generation warning: could not embed image {image_path}: {exc}")
        return flowables

    def _append_analysis_images(
        self,
        result: "PipelineResult",
        elements: list,
        doc,
        styles,
        report_path: Path,
        embedded_images: set[Path],
    ) -> None:
        artifacts = getattr(result, 'artifacts', {}) if hasattr(result, 'artifacts') else {}
        analysis_images = artifacts.get('analysis_images') if isinstance(artifacts, dict) else None
        if not analysis_images:
            return

        resolved_images = []
        for image in analysis_images:
            resolved = self._resolve_asset_path(str(image), report_path)
            if resolved and resolved not in embedded_images:
                resolved_images.append(resolved)

        if not resolved_images:
            return

        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Visual References", styles["Heading2"]))
        elements.append(Spacer(1, 6))

        for image_path in resolved_images:
            elements.extend(self._create_image_flowables(image_path, doc.width, image_path.stem.replace('_', ' ').title(), styles))
    
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
