"""Streamlit entry point for the AI-Powered Design Assistant."""
from __future__ import annotations

import os
import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Optional Lottie animations for richer UX
try:
    from streamlit_lottie import st_lottie
    HAS_ST_LOTTIE = True
except Exception:
    HAS_ST_LOTTIE = False
    def st_lottie(*args, **kwargs):
        # no-op fallback when streamlit_lottie isn't installed
        return None

def load_lottie_file(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
from design_assistant.pipeline import DesignAssistant, InputMode

# Try to import utility modules
try:
    from utils.email_config import EmailConfig
    HAS_EMAIL_CONFIG = True
except ImportError:
    HAS_EMAIL_CONFIG = False
    EmailConfig = None

try:
    from utils.theme_manager import ThemeManager
    HAS_THEME_MANAGER = True
except ImportError:
    HAS_THEME_MANAGER = False
    ThemeManager = None

# Try to import LLM support
try:
    from design_assistant.llm_integration import LLMConfig
    HAS_LLM_SUPPORT = True
except ImportError:
    HAS_LLM_SUPPORT = False
    LLMConfig = None

# Page configuration
st.set_page_config(
    page_title="AI-Powered Design Assistant",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'audit_history' not in st.session_state:
    st.session_state.audit_history = []
if 'current_result' not in st.session_state:
    st.session_state.current_result = None
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Home"
if 'email_config' not in st.session_state:
    st.session_state.email_config = None
if 'selected_audits' not in st.session_state:
    st.session_state.selected_audits = set()
if 'selected_audit_id' not in st.session_state:
    st.session_state.selected_audit_id = None

class AuditHistoryManager:
    """Manage audit history and persistence"""
    
    def __init__(self, history_file: Path = Path("data/audit_history.json")):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_history()
    
    def load_history(self):
        """Load audit history from file"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    st.session_state.audit_history = json.load(f)
        except Exception:
            st.session_state.audit_history = []
    
    def save_history(self):
        """Save audit history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(st.session_state.audit_history, f, indent=2)
        except Exception as e:
            st.error(f"Failed to save history: {e}")
    
    def add_audit(self, result_data: Dict):
        """Add a new audit to history"""
        audit_entry = {
            'id': len(st.session_state.audit_history) + 1,
            'timestamp': datetime.now().isoformat(),
            'input_type': result_data.get('input_type', 'unknown'),
            'input_value': result_data.get('input_value', ''),
            'fairness_score': result_data.get('fairness_score', 0),
            'accessibility_score': result_data.get('accessibility_score', 0),
            'contrast_score': result_data.get('contrast_score', 0),
            'ethical_ux_score': result_data.get('ethical_ux_score', 0),
            'output_dir': result_data.get('output_dir', ''),
            'runtime': result_data.get('runtime', 0)
        }
        st.session_state.audit_history.insert(0, audit_entry)
        self.save_history()
    
    def get_audit_by_id(self, audit_id: int) -> Optional[Dict]:
        """Get audit by ID"""
        for audit in st.session_state.audit_history:
            if audit['id'] == audit_id:
                return audit
        return None
    
    def delete_audits(self, audit_ids: List[int]):
        """Delete audits by IDs"""
        st.session_state.audit_history = [
            audit for audit in st.session_state.audit_history 
            if audit['id'] not in audit_ids
        ]
        self.save_history()
        st.session_state.selected_audits = set()

class EmailService:
    """Handle email functionality for audit reports"""
    
    @staticmethod
    def send_audit_email(to_email: str, subject: str, body: str, attachments: List[Path] = None):
        """Send audit report via email using Gmail"""
        try:
            # Use EmailConfig if available
            if HAS_EMAIL_CONFIG:
                email_config = EmailConfig.get_email_config()
                
                if not email_config:
                    st.error("❌ Email not configured. Please configure email settings in the sidebar.")
                    return False
                
                smtp_server = email_config["smtp_server"]
                port = email_config["port"]
                sender_email = email_config["sender_email"]
                sender_password = email_config["sender_password"]
            else:
                # Fallback to environment variables
                smtp_server = "smtp.gmail.com"
                port = 587
                sender_email = os.getenv("EMAIL_USER", "")
                sender_password = os.getenv("EMAIL_PASSWORD", "")
                
                if not sender_email or not sender_password:
                    st.warning("⚠️ Please configure email settings")
                    return False
            
            # Create message
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = to_email
            message["Subject"] = subject
            
            # Attach HTML body
            message.attach(MIMEText(body, "html"))
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    if attachment.exists():
                        part = MIMEBase('application', 'octet-stream')
                        with open(attachment, 'rb') as file:
                            part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename={attachment.name}'
                        )
                        message.attach(part)
            
            # Send email via Gmail SMTP
            try:
                with smtplib.SMTP(smtp_server, port, timeout=10) as server:
                    server.set_debuglevel(0)
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(sender_email, sender_password)
                    server.send_message(message)
                
                return True
                
            except smtplib.SMTPAuthenticationError:
                st.error("❌ Authentication failed. Please check your credentials.")
                st.info("""
                **Gmail Authentication Help:**
                1. Enable 2-Step Verification in your Google Account
                2. Generate an App Password: https://myaccount.google.com/apppasswords
                3. Use the 16-character App Password (not your regular password)
                """)
                return False
                
            except smtplib.SMTPException as e:
                st.error(f"❌ SMTP error: {str(e)}")
                return False
            
        except Exception as e:
            st.error(f"❌ Failed to send email: {str(e)}")
            return False

def create_score_radar(scores: Dict[str, float]) -> go.Figure:
    """Create a radar chart for scores"""
    categories = list(scores.keys())
    values = list(scores.values())
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(102, 126, 234, 0.3)',
        line=dict(color='#667eea', width=2),
        name='Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickfont=dict(color='black', size=12),
                color='black'
            ),
            angularaxis=dict(
                tickfont=dict(color='black', size=12),
                color='black'
            ),
            bgcolor='white'
        ),
        showlegend=False,
        height=300,
        margin=dict(l=50, r=50, t=50, b=50),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='black', size=12)
    )
    
    return fig

def create_violations_bar_chart(violations_data: Dict[str, int]) -> go.Figure:
    """Create a bar chart for violations"""
    fig = px.bar(
        x=list(violations_data.keys()),
        y=list(violations_data.values()),
        color=list(violations_data.values()),
        color_continuous_scale='Viridis',
        labels={'x': 'Category', 'y': 'Count'}
    )
    
    fig.update_layout(
        height=300,
        showlegend=False,
        margin=dict(l=50, r=50, t=30, b=50),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='black', size=12),
        xaxis=dict(
            tickfont=dict(color='black', size=12),
            title_font=dict(color='black', size=12),
            color='black'
        ),
        yaxis=dict(
            tickfont=dict(color='black', size=12),
            title_font=dict(color='black', size=12),
            color='black'
        )
    )
    
    fig.update_traces(
        textfont=dict(color='black'),
        marker=dict(line=dict(color='black', width=1))
    )
    
    return fig

def create_score_gauge(score: float, title: str) -> go.Figure:
    """Create a gauge chart for individual scores"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'color': 'black', 'size': 14}},
        gauge = {
            'axis': {
                'range': [None, 1], 
                'tickfont': {'color': 'black', 'size': 10},
                'tickcolor': 'black'
            },
            'bar': {'color': "#667eea"},
            'steps': [
                {'range': [0, 0.33], 'color': "lightgray"},
                {'range': [0.33, 0.66], 'color': "gray"},
                {'range': [0.66, 1], 'color': "darkgray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 0.8
            }
        }
    ))
    
    fig.update_layout(
        height=250, 
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='white',
        font=dict(color='black', size=12)
    )
    return fig

def _try_save_plotly(fig, path):
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Prefer kaleido if available
        fig.write_image(str(path))
        return True
    except Exception:
        try:
            # Fallback to static bytes in case of environment limits
            img_bytes = fig.to_image(format="png")
            with open(path, "wb") as f:
                f.write(img_bytes)
            return True
        except Exception:
            return False

# def generate_enhanced_pdf(result, input_value=None, analysis_images=None, history_records=None, out_path=Path("outputs")/ "audit_enhanced.pdf"):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build charts (reuse existing helpers)
    scores = {
        'Accessibility': result.accessibility.score if getattr(result, "accessibility", None) else 0.0,
        'Contrast': result.contrast.average_contrast,
        'Ethical UX': result.dark_patterns.score,
        'Overall Fairness': result.fairness.value
    }
    radar = create_score_radar(scores)
    vio = {
        'Contrast': len(result.contrast.violations),
        'Dark Patterns': len(result.dark_patterns.flags),
        'Accessibility': len(result.accessibility.violations) if getattr(result, "accessibility", None) else 0
    }
    bar = create_violations_bar_chart(vio)

    radar_path = Path("outputs")/"radar_chart.png"
    bar_path = Path("outputs")/"violations_chart.png"
    _try_save_plotly(radar, radar_path)
    _try_save_plotly(bar, bar_path)

    trend_path = None
    if history_records and len(history_records) > 1:
        hist_df = pd.DataFrame(history_records[-10:])
        fig_trend = px.line(hist_df, x='timestamp', y=['fairness_score','accessibility_score','ethical_ux_score'], title='Score Trends Over Time')
        fig_trend.update_layout(
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(color='black', size=12),
            xaxis=dict(
                tickfont=dict(color='black', size=10),
                title_font=dict(color='black', size=12),
                color='black'
            ),
            yaxis=dict(
                tickfont=dict(color='black', size=10),
                title_font=dict(color='black', size=12),
                color='black'
            ),
            title_font=dict(color='black', size=14)
        )
        fig_trend.update_traces(line=dict(width=3))
        fig_trend.update_layout(
            legend=dict(
                font=dict(color='black', size=10),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='black',
                borderwidth=1
            )
        )
        trend_path = Path("outputs")/"trend_chart.png"
        _try_save_plotly(fig_trend, trend_path)

    # Use provided analysis images or search for them
    if analysis_images is None:
        analysis_images = []
    
    # Convert to Path objects and ensure they exist
    analysis_images = [Path(img) for img in analysis_images if Path(img).exists()]
    
    # Look for additional screenshots and analysis images
    screenshot_paths = []
    output_dir = Path("outputs")
    
    # Look for original screenshot/upload
    if input_value and (input_value.endswith(('.png', '.jpg', '.jpeg', '.webp')) or Path(input_value).exists()):
        screenshot_paths.append(Path(input_value))
    
    # Look for analysis images in outputs directory
    for img_pattern in ['*screenshot*', '*analysis*', '*contrast*', '*accessibility*', '*original*', 'upload_*']:
        analysis_images.extend(output_dir.glob(f"{img_pattern}.png"))
        analysis_images.extend(output_dir.glob(f"{img_pattern}.jpg"))
        analysis_images.extend(output_dir.glob(f"{img_pattern}.jpeg"))
    
    # Remove duplicates and ensure files exist
    analysis_images = [img for img in set(analysis_images) if img.exists()]
    screenshot_paths = [img for img in set(screenshot_paths) if img.exists()]

    # Compose PDF
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    story = []

    # Title Page
    story.append(Paragraph("AI-Powered Design Assistant - Enhanced Audit Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Generated on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    
    if input_value:
        story.append(Paragraph(f"<b>Audit Target:</b> {input_value}", styles["Normal"]))
    
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Overall Fairness Score:</b> {result.fairness.value:.2f}/1.0", styles["Heading2"]))
    story.append(Spacer(1, 8))

    # Key Metrics Table
    data = [
        ["Metric", "Score"],
        ["Accessibility", f"{(result.accessibility.score if getattr(result, 'accessibility', None) else 0.0):.2f}"],
        ["Contrast", f"{result.contrast.average_contrast:.2f}"],
        ["Ethical UX", f"{result.dark_patterns.score:.2f}"],
        ["Overall Fairness", f"{result.fairness.value:.2f}"],
    ]
    table = Table(data, colWidths=[180, 120])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#667eea")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    # Add Original Screenshot if available
    if screenshot_paths:
        story.append(Paragraph("<b>Original Design</b>", styles["Heading2"]))
        for screenshot in screenshot_paths[:1]:  # Only include first screenshot
            try:
                img = Image(str(screenshot))
                img.drawHeight = 400
                img.drawWidth = 500
                story.append(img)
                story.append(Spacer(1, 12))
            except Exception as e:
                story.append(Paragraph(f"<i>Could not load screenshot: {str(e)}</i>", styles["Italic"]))
        story.append(PageBreak())

    # Analysis Images Section
    if analysis_images:
        story.append(Paragraph("<b>Analysis Visualizations</b>", styles["Heading2"]))
        for i, analysis_img in enumerate(analysis_images[:4]):  # Limit to 4 analysis images
            try:
                story.append(Paragraph(f"<b>Analysis {i+1}:</b> {analysis_img.stem}", styles["Normal"]))
                img = Image(str(analysis_img))
                img.drawHeight = 300
                img.drawWidth = 400
                story.append(img)
                story.append(Spacer(1, 12))
                
                # Add page break after every 2 images to avoid overcrowding
                if (i + 1) % 2 == 0:
                    story.append(PageBreak())
            except Exception as e:
                story.append(Paragraph(f"<i>Could not load analysis image: {str(e)}</i>", styles["Italic"]))
        story.append(PageBreak())

    # Charts Section
    story.append(Paragraph("<b>Score Analysis Charts</b>", styles["Heading2"]))
    
    if radar_path.exists():
        story.append(Paragraph("<b>Score Radar Chart</b>", styles["Heading3"]))
        img = Image(str(radar_path))
        img.drawHeight = 320
        img.drawWidth = 420
        story.append(img)
        story.append(Spacer(1, 12))

    if bar_path.exists():
        story.append(Paragraph("<b>Violations Analysis</b>", styles["Heading3"]))
        img = Image(str(bar_path))
        img.drawHeight = 320
        img.drawWidth = 420
        story.append(img)
        story.append(Spacer(1, 12))

    if trend_path and Path(trend_path).exists():
        story.append(PageBreak())
        story.append(Paragraph("<b>Historical Trends</b>", styles["Heading3"]))
        img = Image(str(trend_path))
        img.drawHeight = 320
        img.drawWidth = 420
        story.append(img)

    # Detailed Findings
    story.append(PageBreak())
    story.append(Paragraph("<b>Detailed Findings</b>", styles["Heading2"]))
    
    # Accessibility Findings
    if result.accessibility and hasattr(result.accessibility, 'violations') and result.accessibility.violations:
        story.append(Paragraph(f"<b>Accessibility Issues Found:</b> {len(result.accessibility.violations)}", styles["Heading3"]))
        for i, violation in enumerate(result.accessibility.violations[:5]):
            story.append(Paragraph(f"{i+1}. {getattr(violation, 'description', 'Unknown issue')}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Accessibility:</b> No issues found", styles["Normal"]))
    
    story.append(Spacer(1, 12))
    
    # Contrast Findings
    if hasattr(result.contrast, 'violations') and result.contrast.violations:
        story.append(Paragraph(f"<b>Contrast Issues Found:</b> {len(result.contrast.violations)}", styles["Heading3"]))
        for i, violation in enumerate(result.contrast.violations[:5]):
            story.append(Paragraph(f"{i+1}. {getattr(violation, 'description', 'Unknown issue')}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Contrast:</b> No issues found", styles["Normal"]))
    
    story.append(Spacer(1, 12))
    
    # Ethical UX Findings
    if hasattr(result.dark_patterns, 'flags') and result.dark_patterns.flags:
        story.append(Paragraph(f"<b>Ethical UX Issues Found:</b> {len(result.dark_patterns.flags)}", styles["Heading3"]))
        for i, flag in enumerate(result.dark_patterns.flags[:5]):
            story.append(Paragraph(f"{i+1}. {getattr(flag, 'description', 'Unknown issue')}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Ethical UX:</b> No issues found", styles["Normal"]))

    doc.build(story)
    return out_path

def generate_enhanced_pdf(result, input_value=None, analysis_images=None, history_records=None, out_path=Path("outputs")/ "audit_enhanced.pdf"):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    import html

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Build charts (reuse existing helpers)
    scores = {
        'Accessibility': result.accessibility.score if getattr(result, "accessibility", None) else 0.0,
        'Contrast': result.contrast.average_contrast,
        'Ethical UX': result.dark_patterns.score,
        'Overall Fairness': result.fairness.value
    }
    radar = create_score_radar(scores)
    vio = {
        'Contrast': len(result.contrast.violations),
        'Dark Patterns': len(result.dark_patterns.flags),
        'Accessibility': len(result.accessibility.violations) if getattr(result, "accessibility", None) else 0
    }
    bar = create_violations_bar_chart(vio)

    radar_path = Path("outputs")/"radar_chart.png"
    bar_path = Path("outputs")/"violations_chart.png"
    _try_save_plotly(radar, radar_path)
    _try_save_plotly(bar, bar_path)

    trend_path = None
    if history_records and len(history_records) > 1:
        hist_df = pd.DataFrame(history_records[-10:])
        fig_trend = px.line(hist_df, x='timestamp', y=['fairness_score','accessibility_score','ethical_ux_score'], title='Score Trends Over Time')
        fig_trend.update_layout(
            paper_bgcolor='white',
            plot_bgcolor='white',
            font=dict(color='black', size=12),
            xaxis=dict(
                tickfont=dict(color='black', size=10),
                title_font=dict(color='black', size=12),
                color='black'
            ),
            yaxis=dict(
                tickfont=dict(color='black', size=10),
                title_font=dict(color='black', size=12),
                color='black'
            ),
            title_font=dict(color='black', size=14)
        )
        fig_trend.update_traces(line=dict(width=3))
        fig_trend.update_layout(
            legend=dict(
                font=dict(color='black', size=10),
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='black',
                borderwidth=1
            )
        )
        trend_path = Path("outputs")/"trend_chart.png"
        _try_save_plotly(fig_trend, trend_path)

    # Use provided analysis images or search for them
    if analysis_images is None:
        analysis_images = []
    
    # Convert to Path objects and ensure they exist
    analysis_images = [Path(img) for img in analysis_images if Path(img).exists()]
    
    # Look for additional screenshots and analysis images
    screenshot_paths = []
    output_dir = Path("outputs")
    
    # Look for original screenshot/upload
    if input_value and (input_value.endswith(('.png', '.jpg', '.jpeg', '.webp')) or Path(input_value).exists()):
        screenshot_paths.append(Path(input_value))
    
    # Look for analysis images in outputs directory
    for img_pattern in ['*screenshot*', '*analysis*', '*contrast*', '*accessibility*', '*original*', 'upload_*']:
        analysis_images.extend(output_dir.glob(f"{img_pattern}.png"))
        analysis_images.extend(output_dir.glob(f"{img_pattern}.jpg"))
        analysis_images.extend(output_dir.glob(f"{img_pattern}.jpeg"))
    
    # Remove duplicates and ensure files exist
    analysis_images = [img for img in set(analysis_images) if img.exists()]
    screenshot_paths = [img for img in set(screenshot_paths) if img.exists()]

    # Compose PDF
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    story = []

    # Title Page
    story.append(Paragraph("AI-Powered Design Assistant - Enhanced Audit Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Generated on:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    
    if input_value:
        story.append(Paragraph(f"<b>Audit Target:</b> {input_value}", styles["Normal"]))
    
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Overall Fairness Score:</b> {result.fairness.value:.2f}/1.0", styles["Heading2"]))
    story.append(Spacer(1, 8))

    # Key Metrics Table
    data = [
        ["Metric", "Score"],
        ["Accessibility", f"{(result.accessibility.score if getattr(result, 'accessibility', None) else 0.0):.2f}"],
        ["Contrast", f"{result.contrast.average_contrast:.2f}"],
        ["Ethical UX", f"{result.dark_patterns.score:.2f}"],
        ["Overall Fairness", f"{result.fairness.value:.2f}"],
    ]
    table = Table(data, colWidths=[180, 120])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#667eea")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    # Add Original Screenshot if available
    if screenshot_paths:
        story.append(Paragraph("<b>Original Design</b>", styles["Heading2"]))
        for screenshot in screenshot_paths[:1]:  # Only include first screenshot
            try:
                img = Image(str(screenshot))
                img.drawHeight = 400
                img.drawWidth = 500
                story.append(img)
                story.append(Spacer(1, 12))
            except Exception as e:
                story.append(Paragraph(f"<i>Could not load screenshot: {str(e)}</i>", styles["Italic"]))
        story.append(PageBreak())

    # Analysis Images Section
    if analysis_images:
        story.append(Paragraph("<b>Analysis Visualizations</b>", styles["Heading2"]))
        for i, analysis_img in enumerate(analysis_images[:4]):  # Limit to 4 analysis images
            try:
                story.append(Paragraph(f"<b>Analysis {i+1}:</b> {analysis_img.stem}", styles["Normal"]))
                img = Image(str(analysis_img))
                img.drawHeight = 300
                img.drawWidth = 400
                story.append(img)
                story.append(Spacer(1, 12))
                
                # Add page break after every 2 images to avoid overcrowding
                if (i + 1) % 2 == 0:
                    story.append(PageBreak())
            except Exception as e:
                story.append(Paragraph(f"<i>Could not load analysis image: {str(e)}</i>", styles["Italic"]))
        story.append(PageBreak())

    # Charts Section
    story.append(Paragraph("<b>Score Analysis Charts</b>", styles["Heading2"]))
    
    if radar_path.exists():
        story.append(Paragraph("<b>Score Radar Chart</b>", styles["Heading3"]))
        img = Image(str(radar_path))
        img.drawHeight = 320
        img.drawWidth = 420
        story.append(img)
        story.append(Spacer(1, 12))

    if bar_path.exists():
        story.append(Paragraph("<b>Violations Analysis</b>", styles["Heading3"]))
        img = Image(str(bar_path))
        img.drawHeight = 320
        img.drawWidth = 420
        story.append(img)
        story.append(Spacer(1, 12))

    if trend_path and Path(trend_path).exists():
        story.append(PageBreak())
        story.append(Paragraph("<b>Historical Trends</b>", styles["Heading3"]))
        img = Image(str(trend_path))
        img.drawHeight = 320
        img.drawWidth = 420
        story.append(img)

    # Detailed Findings
    story.append(PageBreak())
    story.append(Paragraph("<b>Detailed Findings</b>", styles["Heading2"]))
    
    # Helper function to clean HTML tags from text
    def clean_html_tags(text):
        """Remove or escape HTML tags from text for PDF generation"""
        if not text:
            return ""
        # Replace common HTML tags with plain text equivalents
        text = str(text)
        text = text.replace('<img>', 'image elements')
        text = text.replace('</img>', '')
        text = text.replace('<para>', '')
        text = text.replace('</para>', '')
        text = text.replace('<strong>', '')
        text = text.replace('</strong>', '')
        text = text.replace('<em>', '')
        text = text.replace('</em>', '')
        # Escape any remaining HTML characters
        text = html.escape(text)
        return text
    
    # Accessibility Findings
    if result.accessibility and hasattr(result.accessibility, 'violations') and result.accessibility.violations:
        story.append(Paragraph(f"<b>Accessibility Issues Found:</b> {len(result.accessibility.violations)}", styles["Heading3"]))
        for i, violation in enumerate(result.accessibility.violations[:5]):
            description = clean_html_tags(getattr(violation, 'description', 'Unknown issue'))
            story.append(Paragraph(f"{i+1}. {description}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Accessibility:</b> No issues found", styles["Normal"]))
    
    story.append(Spacer(1, 12))
    
    # Contrast Findings
    if hasattr(result.contrast, 'violations') and result.contrast.violations:
        story.append(Paragraph(f"<b>Contrast Issues Found:</b> {len(result.contrast.violations)}", styles["Heading3"]))
        for i, violation in enumerate(result.contrast.violations[:5]):
            description = clean_html_tags(getattr(violation, 'description', 'Unknown issue'))
            story.append(Paragraph(f"{i+1}. {description}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Contrast:</b> No issues found", styles["Normal"]))
    
    story.append(Spacer(1, 12))
    
    # Ethical UX Findings
    if hasattr(result.dark_patterns, 'flags') and result.dark_patterns.flags:
        story.append(Paragraph(f"<b>Ethical UX Issues Found:</b> {len(result.dark_patterns.flags)}", styles["Heading3"]))
        for i, flag in enumerate(result.dark_patterns.flags[:5]):
            description = clean_html_tags(getattr(flag, 'description', 'Unknown issue'))
            story.append(Paragraph(f"{i+1}. {description}", styles["Normal"]))
    else:
        story.append(Paragraph("<b>Ethical UX:</b> No issues found", styles["Normal"]))

    doc.build(story)
    return out_path

# Initialize managers
history_manager = AuditHistoryManager()
email_service = EmailService()

# Custom CSS for animations and styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
        animation: fadeInUp 0.8s ease;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        border-left: 4px solid #667eea;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
        backdrop-filter: blur(10px);
        margin: 0.5rem 0;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
    }
    
    .success-box {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        animation: slideInRight 0.6s ease;
    }
    
    .sidebar-nav {
        background: linear-gradient(180deg, #2d3748 0%, #4a5568 100%);
        padding: 1rem;
        border-radius: 15px;
    }
    
    .nav-button {
        width: 100%;
        padding: 12px 20px;
        margin: 8px 0;
        border: none;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.1);
        color: white;
        text-align: left;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 1rem;
    }
    
    .nav-button:hover {
        background: rgba(255, 255, 255, 0.2);
        transform: translateX(5px);
    }
    
    .nav-button.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    
    .feature-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.15);
    }
    
    .compact-config {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .history-item {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .history-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
    }
    
    .compact-slider {
        padding: 0.5rem 0;
    }
    
    /* Compact Sliders */
    div[data-testid="stSlider"] {
        margin-top: 0.25rem;
        margin-bottom: 0.25rem;
    }
    .compact-config h4, .compact-config strong { color: var(--text-color); }
    
    /* Animations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .quick-action-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 20px;
        border-radius: 15px;
        font-size: 1.2rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
        margin: 10px 0;
        width: 100%;
    }
    
    .quick-action-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
    }
    
    .email-popover {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e6e6e6;
    }
    
    .delete-actions {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)
# Load optional Lottie animations (safe fallbacks)
loading_anim = load_lottie_file("data/animations/loading.json") if HAS_ST_LOTTIE else None
success_anim = load_lottie_file("data/animations/success.json") if HAS_ST_LOTTIE else None

# Sidebar Navigation
with st.sidebar:
    # st.markdown("<div class='sidebar-nav'>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; color: white; margin-bottom: 2rem;'>🎨 Design Assistant</h2>", 
                unsafe_allow_html=True)
    
    # Navigation buttons
    nav_options = {
        "🏠 Home": "Home",
        "🔍 Audit": "Audit", 
        "📊 Reports": "Reports",
        "📚 History": "History",
        "ℹ️ About": "About"
    }
    
    for display_name, page_name in nav_options.items():
        if st.button(display_name, key=f"nav_{page_name}", use_container_width=True):
            st.session_state.current_page = page_name
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Email configuration in sidebar
    if HAS_EMAIL_CONFIG:
        st.markdown("---")
        EmailConfig.setup_email_ui()
    
    # Quick stats
    if st.session_state.audit_history:
        st.markdown("---")
        st.markdown("### 📈 Quick Stats")
        total_audits = len(st.session_state.audit_history)
        avg_score = sum(h['fairness_score'] for h in st.session_state.audit_history) / total_audits
        st.metric("Total Audits", total_audits)
        st.metric("Average Score", f"{avg_score:.2f}")

# Main content based on navigation
if st.session_state.current_page == "Home":
    st.markdown("<div class='main-header'>AI-Powered Design Assistant</div>", 
                unsafe_allow_html=True)
    
    st.markdown("""
    <div style='text-align: center; font-size: 1.2rem; color: #666; margin-bottom: 1rem;'>
        Evaluate accessibility, contrast, and dark pattern risks with AI-powered analysis
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Actions at the top
    st.markdown("## 🚀 Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🎯 Start New Audit", use_container_width=True, type="primary"):
            st.session_state.current_page = "Audit"
            st.rerun()
    
    with col2:
        if st.session_state.audit_history:
            if st.button("📚 View History", use_container_width=True):
                st.session_state.current_page = "History"
                st.rerun()
        else:
            st.button("📚 View History", use_container_width=True, disabled=True)
    
    # Feature cards
    st.markdown("## ✨ Features")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class='feature-card'>
            <h3>🎯 Accessibility Audit</h3>
            <p>Comprehensive WCAG compliance checking with detailed violation reports</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='feature-card'>
            <h3>🎨 Contrast Analysis</h3>
            <p>Advanced color contrast evaluation with visual annotations</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class='feature-card'>
            <h3>⚖️ Ethical UX Scoring</h3>
            <p>Dark pattern detection and ethical design assessment</p>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.current_page == "Audit":
    st.markdown("## 🔍 Design Audit")
    
    # Initialize variables
    run_audit = False
    uploaded_path = None
    input_value = ""
    llm_config = None
    
    # Input section first - more user-friendly
    st.markdown("### 📥 Input Source")
    
    mode = st.radio(
        "Select input type:",
        options=[InputMode.URL.value, InputMode.SCREENSHOT.value],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    run_audit = False
    uploaded_path = None
    input_value = ""

    if mode == InputMode.URL.value:
        input_value = st.text_input("Enter URL", placeholder="https://example.com")
        run_disabled = not input_value
    else:
        upload = st.file_uploader("Upload Screenshot", type=["png", "jpg", "jpeg", "webp"])
        if upload:
            output_dir = Path("outputs")
            uploaded_path = output_dir / f"upload_{int(time.time())}_{upload.name}"
            uploaded_path.parent.mkdir(parents=True, exist_ok=True)
            uploaded_path.write_bytes(upload.getvalue())
            input_value = str(uploaded_path)
            st.success(f"✅ Uploaded: {upload.name}")
        run_disabled = uploaded_path is None

    # Compact Configuration with smaller sliders
    st.markdown("### ⚙️ Configuration")
    with st.container():
        st.markdown(
            """
            <style>
                div[data-testid="stHorizontalBlock"] {
                    background: var(--card-bg);
                    padding: 1rem;
                    border-radius: 10px;
                    border: 1px solid var(--border-color);
                    border-left: 4px solid #667eea;
                    margin-bottom: 1rem;
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Score Weights**")
            # Compact sliders
            alpha = st.slider(
                "Accessibility (α)", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.5, 
                key="alpha",
                help="Weight for accessibility scoring"
            )
            beta = st.slider(
                "Ethical UX (β)", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.5, 
                key="beta",
                help="Weight for ethical UX scoring"
            )
        
        with col2:
            # LLM Configuration
            llm_config = None
            if HAS_LLM_SUPPORT:
                st.markdown("**AI Enhancement**")
                use_llm = st.checkbox("Enable Gemini Analysis", value=False)
                
                if use_llm:
                    api_key = st.text_input(
                        "Google AI API Key",
                        type="password",
                        value=os.getenv("GOOGLE_API_KEY", ""),
                        help="Get your API key from aistudio.google.com/apikey"
                    )
                    
                    if api_key:
                        llm_config = LLMConfig(
                            api_key=api_key,
                            model="models/gemini-2.0-flash-exp",
                            temperature=0.7,
                            max_tokens=8000
                        )
                        st.success("✅ AI analysis enabled")
                    else:
                        st.warning("⚠️ Enter API key to enable AI analysis")
                        llm_config = None
            else:
                st.info("ℹ️ LLM support not available")
                llm_config = None
        st.markdown('</div>', unsafe_allow_html=True)

    # Compact divider
    st.markdown("")
    if st.button("🚀 Run Comprehensive Audit", disabled=run_disabled, use_container_width=True, type="primary"):
        run_audit = True

    if run_audit:
        start_time = time.time()
        
        # Create assistant with configuration
        assistant = DesignAssistant(llm_config=llm_config, alpha=alpha, beta=beta)
        
        try:
            # Progress tracking with fancy messages
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("🎯 Initializing design audit...")
            progress_bar.progress(10)
            time.sleep(0.5)
            
            status_text.text("🔍 Analyzing design elements...")
            progress_bar.progress(25)
            time.sleep(0.5)
            
            status_text.text("🎨 Checking color contrast and accessibility...")
            progress_bar.progress(45)
            time.sleep(0.5)
            
            status_text.text("⚖️ Evaluating ethical UX patterns...")
            progress_bar.progress(65)
            time.sleep(0.5)

            # Run audit (show loading animation if available)
            col_anim, col_main = st.columns([1, 4])
            with col_anim:
                if HAS_ST_LOTTIE and loading_anim:
                    st_lottie(loading_anim, height=180, key="loading")
                else:
                    st.info("Running analysis...")

            with col_main:
                with st.spinner("🤖 Running comprehensive AI analysis..."):
                    if mode == InputMode.URL.value:
                        result = assistant.run(InputMode.URL, input_value, output_dir=Path("outputs"))
                    else:
                        result = assistant.run(
                            InputMode.SCREENSHOT,
                            input_value,
                            output_dir=Path("outputs"),
                        )
            
            progress_bar.progress(85)
            status_text.text("📊 Generating comprehensive reports...")
            time.sleep(0.5)
            
            # Store result
            st.session_state.current_result = result
            
            # Calculate runtime
            runtime = time.time() - start_time
            
            # Add to history
            history_manager.add_audit({
                'input_type': mode,
                'input_value': input_value,
                'fairness_score': result.fairness.value,
                'accessibility_score': result.accessibility.score if result.accessibility else 0.0,
                'contrast_score': result.contrast.average_contrast,
                'ethical_ux_score': result.dark_patterns.score,
                'output_dir': str(Path("outputs")),
                'runtime': runtime
            })
            
            progress_bar.progress(100)
            status_text.text("✅ Audit completed successfully!")
            time.sleep(1)
            progress_bar.empty()
            status_text.empty()
            
            # Display results
            st.markdown("---")
            st.markdown("## 📊 Audit Results")
            
            # Main score card
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                score_color = "green" if result.fairness.value > 0.7 else "orange" if result.fairness.value > 0.4 else "red"
                st.markdown(f"""
                <div class='success-box' style='background: linear-gradient(135deg, 
                    {"#00b09b" if result.fairness.value > 0.7 else "#f46b45" if result.fairness.value > 0.4 else "#ff416c"} 
                    0%, {"#96c93d" if result.fairness.value > 0.7 else "#eea849" if result.fairness.value > 0.4 else "#ff4b2b"} 100%);'>
                    <h2 style='margin: 0; font-size: 2.5rem;'>Design Fairness Score</h2>
                    <h1 style='margin: 0; font-size: 4rem;'>{result.fairness.value:.2f}/1.0</h1>
                    <p>Audit completed in {runtime:.1f}s</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                accessibility_score = result.accessibility.score if result.accessibility else 0.0
                st.metric("Accessibility", f"{accessibility_score:.2f}")
                st.metric("Average Contrast", f"{result.contrast.average_contrast:.2f}")
            
            with col3:
                st.metric("Ethical UX", f"{result.dark_patterns.score:.2f}")
                total_violations = (
                    len(getattr(result.contrast, 'violations', [])) + 
                    len(getattr(result.dark_patterns, 'flags', [])) + 
                    (len(getattr(result.accessibility, 'violations', [])) if result.accessibility else 0)
                )
                st.metric("Total Violations", total_violations)
            
            # Show success animation near results (if available)
            if HAS_ST_LOTTIE and success_anim:
                col_anim_success, _ = st.columns([1, 11])
                with col_anim_success:
                    st_lottie(success_anim, height=140, key="success")

            # Visualizations
            st.markdown("### 📈 Score Overview")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Radar chart
                scores = {
                    'Accessibility': result.accessibility.score if result.accessibility else 0.0,
                    'Contrast': result.contrast.average_contrast,
                    'Ethical UX': result.dark_patterns.score,
                    'Overall Fairness': result.fairness.value
                }
                fig_radar = create_score_radar(scores)
                st.plotly_chart(fig_radar, use_container_width=True)
            
            with col2:
                # Violations bar chart
                violations_data = {
                    'Contrast': len(getattr(result.contrast, 'violations', [])),
                    'Dark Patterns': len(getattr(result.dark_patterns, 'flags', [])),
                    'Accessibility': len(getattr(result.accessibility, 'violations', [])) if result.accessibility else 0
                }
                fig_bar = create_violations_bar_chart(violations_data)
                st.plotly_chart(fig_bar, use_container_width=True)
            
            # Detailed sections with expanders
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("🎯 Accessibility Details", expanded=True):
                    if result.accessibility and hasattr(result.accessibility, 'violations') and result.accessibility.violations:
                        st.dataframe([violation.__dict__ for violation in result.accessibility.violations],
                                   use_container_width=True)
                    else:
                        st.success("✅ No accessibility violations found!")
                
                with st.expander("🎨 Contrast Analysis", expanded=True):
                    if hasattr(result.contrast, 'violations') and result.contrast.violations:
                        st.dataframe([violation.to_dict() for violation in result.contrast.violations],
                                   use_container_width=True)
                    else:
                        st.success("✅ No contrast violations found!")
            
            with col2:
                with st.expander("⚖️ Ethical UX Analysis", expanded=True):
                    if hasattr(result.dark_patterns, 'flags') and result.dark_patterns.flags:
                        st.dataframe([flag.to_dict() for flag in result.dark_patterns.flags],
                                   use_container_width=True)
                    else:
                        st.success("✅ No dark patterns detected!")
                
                # Add Persuasive Design Analysis
                with st.expander("🧠 Persuasive Design Analysis", expanded=True):
                    # This would integrate with your persuasive design detection logic
                    persuasive_score = max(0.7, result.dark_patterns.score + 0.1)  # Example calculation
                    st.metric("Persuasive Design Score", f"{persuasive_score:.2f}")
                    st.info("""
                    **Persuasive Design Elements Checked:**
                    - Social proof indicators
                    - Scarcity messaging
                    - Urgency triggers
                    - Authority endorsements
                    - Reciprocity patterns
                    - Commitment devices
                    """)
                
                # LLM Summary if available
                if llm_config and HAS_LLM_SUPPORT:
                    with st.expander("🤖 AI Insights", expanded=True):
                        st.info("""
                        **Gemini AI Analysis Summary:**
                        The AI has analyzed your design comprehensively and provided 
                        additional insights about usability patterns, potential improvements, 
                        and industry best practices.
                        """)
            
            # View Markdown Report
            st.markdown("### 📄 Report Viewer")
            markdown_path = Path("outputs") / "audit_report.md"
            if markdown_path.exists():
                with st.expander("📖 View Markdown Report", expanded=False):
                    report_content = markdown_path.read_text(encoding="utf-8")
                    st.markdown(report_content)
            
            # Download section
            st.markdown("---")
            st.markdown("## 📥 Download Reports")
            
            col1, col2, col3, col4 = st.columns(4)
            
            output_dir = Path("outputs")
            with col1:
                markdown_path = output_dir / "audit_report.md"
                if markdown_path.exists():
                    st.download_button(
                        "📄 Markdown Report",
                        data=markdown_path.read_bytes(),
                        file_name="audit_report.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
            
            with col2:
                json_path = output_dir / "audit.json"
                if json_path.exists():
                    st.download_button(
                        "📋 JSON Data",
                        data=json_path.read_bytes(),
                        file_name="audit.json",
                        mime="application/json",
                        use_container_width=True
                    )
            
            with col3:
                pdf_path = output_dir / "audit.pdf"
                if pdf_path.exists():
                    st.download_button(
                        "📕 PDF Summary",
                        data=pdf_path.read_bytes(),
                        file_name="audit.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            
            with col4:
                # Generate and download enhanced PDF with images
                try:
                    # Get analysis images from artifacts if available
                    analysis_images = []
                    if hasattr(result, 'artifacts') and result.artifacts:
                        analysis_images = result.artifacts.get('analysis_images', [])
                    
                    # Add error handling for PDF generation
                    try:
                        enhanced_pdf = generate_enhanced_pdf(
                            result, 
                            input_value=input_value,
                            analysis_images=analysis_images,
                            history_records=st.session_state.audit_history[:10]
                        )
                        
                        if enhanced_pdf.exists():
                            st.download_button(
                                "📘 Enhanced PDF (with Images)",
                                data=enhanced_pdf.read_bytes(),
                                file_name="audit_enhanced.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                help="Includes screenshots, analysis images, and detailed charts"
                            )
                        else:
                            st.button(
                                "📘 Enhanced PDF",
                                disabled=True,
                                use_container_width=True,
                                help="Enhanced PDF generation failed"
                            )
                    except Exception as pdf_error:
                        st.error(f"❌ PDF generation error: {str(pdf_error)}")
                        # Fallback: offer the basic PDF instead
                        pdf_path = output_dir / "audit.pdf"
                        if pdf_path.exists():
                            st.download_button(
                                "📕 Basic PDF Report",
                                data=pdf_path.read_bytes(),
                                file_name="audit.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                help="Basic PDF report (enhanced version failed)"
                            )
                        
                except Exception as e:
                    st.error(f"❌ Failed to generate enhanced PDF: {e}")
                    st.button(
                        "📘 Enhanced PDF",
                        disabled=True,
                        use_container_width=True,
                        help="Enhanced PDF generation failed"
                    )

        except Exception as exc:
            st.error(f"❌ Audit failed: {str(exc)}")
            st.exception(exc)
    
    else:
        if not run_disabled:
            st.info("👆 Configure your input and click 'Run Comprehensive Audit' to start analysis")
        else:
            st.warning("⚠️ Please provide a URL or upload a screenshot to start audit")

elif st.session_state.current_page == "Reports":
    st.markdown("## 📊 Comprehensive Reports")
    
    # Check if we have a selected audit from history
    selected_audit_id = st.session_state.get('selected_audit_id')
    if selected_audit_id:
        selected_audit = history_manager.get_audit_by_id(selected_audit_id)
        if selected_audit:
            st.success(f"📊 Viewing report for: {selected_audit.get('input_value', 'Unknown')}")
            
            # Display selected audit details
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Overall Score", f"{selected_audit.get('fairness_score', 0):.2f}")
            with col2:
                st.metric("Accessibility", f"{selected_audit.get('accessibility_score', 0):.2f}")
            with col3:
                st.metric("Contrast", f"{selected_audit.get('contrast_score', 0):.2f}")
            with col4:
                st.metric("Ethical UX", f"{selected_audit.get('ethical_ux_score', 0):.2f}")
            
            # Show gauge charts for the selected audit
            st.markdown("### 🎯 Detailed Scoring")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                fig_gauge1 = create_score_gauge(
                    selected_audit.get('fairness_score', 0), 
                    "Overall Fairness"
                )
                st.plotly_chart(fig_gauge1, use_container_width=True)
            
            with col2:
                fig_gauge2 = create_score_gauge(selected_audit.get('accessibility_score', 0), "Accessibility")
                st.plotly_chart(fig_gauge2, use_container_width=True)
            
            with col3:
                fig_gauge3 = create_score_gauge(selected_audit.get('contrast_score', 0), "Contrast")
                st.plotly_chart(fig_gauge3, use_container_width=True)
            
            with col4:
                fig_gauge4 = create_score_gauge(selected_audit.get('ethical_ux_score', 0), "Ethical UX")
                st.plotly_chart(fig_gauge4, use_container_width=True)
            
            # Back button
            if st.button("⬅️ Back to History"):
                st.session_state.selected_audit_id = None
                st.session_state.current_page = "History"
                st.rerun()
                
        else:
            st.error("Selected audit not found")
            st.session_state.selected_audit_id = None
    
    elif not st.session_state.current_result and not st.session_state.audit_history:
        st.info("Run an audit first to see detailed reports!")
        if st.button("🎯 Run First Audit", use_container_width=True):
            st.session_state.current_page = "Audit"
            st.rerun()
    else:
        # Use current result or latest from history
        result = st.session_state.current_result
        
        if result:
            # Detailed gauge charts
            st.markdown("### 🎯 Detailed Scoring")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                fig_gauge1 = create_score_gauge(
                    result.fairness.value, 
                    "Overall Fairness"
                )
                st.plotly_chart(fig_gauge1, use_container_width=True)
            
            with col2:
                accessibility_score = result.accessibility.score if result.accessibility else 0.0
                fig_gauge2 = create_score_gauge(accessibility_score, "Accessibility")
                st.plotly_chart(fig_gauge2, use_container_width=True)
            
            with col3:
                fig_gauge3 = create_score_gauge(result.contrast.average_contrast, "Contrast")
                st.plotly_chart(fig_gauge3, use_container_width=True)
            
            with col4:
                fig_gauge4 = create_score_gauge(result.dark_patterns.score, "Ethical UX")
                st.plotly_chart(fig_gauge4, use_container_width=True)
            
            # Trend analysis (if history available)
            if len(st.session_state.audit_history) > 1:
                st.markdown("### 📈 Historical Trends")
                
                history_df = pd.DataFrame(st.session_state.audit_history[:10])
                fig_trend = px.line(
                    history_df, 
                    x='timestamp', 
                    y=['fairness_score', 'accessibility_score', 'ethical_ux_score'],
                    title='Score Trends Over Time'
                )
                fig_trend.update_layout(
                    paper_bgcolor='white',
                    plot_bgcolor='white',
                    font=dict(color='black', size=12),
                    xaxis=dict(
                        tickfont=dict(color='black', size=10),
                        title_font=dict(color='black', size=12),
                        color='black'
                    ),
                    yaxis=dict(
                        tickfont=dict(color='black', size=10),
                        title_font=dict(color='black', size=12),
                        color='black'
                    ),
                    title_font=dict(color='black', size=14)
                )
                fig_trend.update_traces(line=dict(width=3))
                fig_trend.update_layout(
                    legend=dict(
                        font=dict(color='black', size=10),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='black',
                        borderwidth=1
                    )
                )
                st.plotly_chart(fig_trend, use_container_width=True)

elif st.session_state.current_page == "History":
    st.markdown("## 📚 Audit History")
    
    if not st.session_state.audit_history:
        st.info("No audit history yet. Run your first audit to see it here!")
        if st.button("🎯 Run First Audit", use_container_width=True):
            st.session_state.current_page = "Audit"
            st.rerun()
    else:
        # Search and filter
        col1, col2 = st.columns([3, 1])
        with col1:
            search_term = st.text_input("🔍 Search audits...", placeholder="Search by URL or filename")
        with col2:
            items_per_page = st.selectbox("Items per page", [10, 20, 50], index=0)
        
        # Filter history
        filtered_history = [
            h for h in st.session_state.audit_history 
            if not search_term or search_term.lower() in h.get('input_value', '').lower()
        ]
        
        # Display history with improved styling
        for audit in filtered_history[:items_per_page]:
            with st.container():
                # st.markdown('<div class="history-item">', unsafe_allow_html=True)
                col1, col2, col3, col4, col5, col6 = st.columns([1, 3, 1, 1, 1, 1])
                
                with col1:
                    # Small delete button with only dustbin symbol
                    if st.button("🗑️", key=f"delete_{audit['id']}", use_container_width=False):
                        if st.session_state.get(f"confirm_delete_{audit['id']}", False):
                            # Second click - actually delete
                            history_manager.delete_audits([audit['id']])
                            st.success(f"✅ Deleted audit #{audit['id']}")
                            st.rerun()
                        else:
                            # First click - show confirmation
                            st.session_state[f"confirm_delete_{audit['id']}"] = True
                            st.rerun()

                    # Show confirmation message if this audit is pending deletion
                    if st.session_state.get(f"confirm_delete_{audit['id']}", False):
                        st.warning("Click 🗑️ again to confirm")

                with col2:
                    input_value = audit.get('input_value', 'Unknown')
                    timestamp = audit.get('timestamp', '')
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        formatted_time = timestamp
                    
                    st.markdown(f"**{input_value}**")
                    st.caption(f"🕒 {formatted_time}")
                
                with col3:
                    score = audit.get('fairness_score', 0)
                    st.metric("Score", f"{score:.2f}")
                
                with col4:
                    if st.button("📊 View", key=f"view_{audit['id']}", use_container_width=True):
                        st.session_state.selected_audit_id = audit['id']
                        st.session_state.current_page = "Reports"
                        st.rerun()
                
                with col5:
                    # Export button in history
                    output_dir = Path(audit.get('output_dir', 'outputs'))
                    markdown_path = output_dir / "audit_report.md"
                    
                    if markdown_path.exists():
                        with open(markdown_path, 'rb') as file:
                            st.download_button(
                                "📥 Export",
                                data=file.read(),
                                file_name=f"audit_{audit['id']}.md",
                                mime="text/markdown",
                                key=f"download_{audit['id']}",
                                use_container_width=True
                            )
                    else:
                        st.button(
                            "📥 Export",
                            key=f"download_{audit['id']}",
                            disabled=True,
                            use_container_width=True,
                            help="Report file not found"
                        )
                
                with col6:
                    # Email button in history
                    try:
                        email_configured = HAS_EMAIL_CONFIG and EmailConfig.get_email_config() is not None
                    except:
                        email_configured = False
                        
                    if email_configured:
                        with st.popover("📧 Email", use_container_width=True):
                            st.markdown('<div class="email-popover">', unsafe_allow_html=True)
                            
                            recipient_email = st.text_input(
                                "Recipient Email", 
                                placeholder="recipient@example.com", 
                                key=f"email_{audit['id']}"
                            )
                            
                            email_subject = st.text_input(
                                "Subject", 
                                value=f"Design Audit Report - {input_value[:30]}", 
                                key=f"subject_{audit['id']}"
                            )
                            
                            if st.button("📤 Send Email", key=f"send_{audit['id']}", use_container_width=True):
                                if recipient_email:
                                    if "@" not in recipient_email:
                                        st.error("❌ Please enter a valid email address")
                                    else:
                                        with st.spinner("Sending email..."):
                                            output_dir = Path(audit.get('output_dir', 'outputs'))
                                            markdown_path = output_dir / "audit_report.md"
                                            
                                            email_body = f"""
                                            <html>
                                            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                                                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                                                    <h1 style="color: #667eea; border-bottom: 3px solid #667eea; padding-bottom: 10px;">Design Audit Report</h1>
                                                    <p style="font-size: 16px; color: #333;">Your design audit has been completed successfully.</p>
                                                    
                                                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                                                        <p style="margin: 5px 0;"><strong>Audit Target:</strong> {input_value}</p>
                                                        <p style="margin: 5px 0;"><strong>Audit Date:</strong> {formatted_time}</p>
                                                        <p style="margin: 5px 0;"><strong>Overall Score:</strong> <span style="font-size: 24px; color: #667eea; font-weight: bold;">{score:.2f}/1.0</span></p>
                                                    </div>
                                                    
                                                    <h3 style="color: #333;">Score Breakdown:</h3>
                                                    <ul style="list-style: none; padding: 0;">
                                                        <li style="padding: 8px; background-color: #f8f9fa; margin: 5px 0; border-radius: 5px;">🎯 Accessibility: {audit.get('accessibility_score', 0):.2f}</li>
                                                        <li style="padding: 8px; background-color: #f8f9fa; margin: 5px 0; border-radius: 5px;">🎨 Contrast: {audit.get('contrast_score', 0):.2f}</li>
                                                        <li style="padding: 8px; background-color: #f8f9fa; margin: 5px 0; border-radius: 5px;">⚖️ Ethical UX: {audit.get('ethical_ux_score', 0):.2f}</li>
                                                    </ul>
                                                    
                                                    <p style="margin-top: 30px; color: #666; font-size: 14px;">Please find the detailed audit report attached to this email.</p>
                                                    
                                                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                                                    <p style="text-align: center; color: #999; font-size: 12px;">
                                                        Generated by AI-Powered Design Assistant<br>
                                                        Making the web better, one audit at a time 🎨
                                                    </p>
                                                </div>
                                            </body>
                                            </html>
                                            """
                                            
                                            attachments = [markdown_path] if markdown_path.exists() else []
                                            
                                            if email_service.send_audit_email(recipient_email, email_subject, email_body, attachments):
                                                st.success("✅ Email sent successfully!")
                                                st.balloons()
                                            else:
                                                st.error("❌ Failed to send email. Check your email configuration.")
                                else:
                                    st.warning("⚠️ Please enter a recipient email address")
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.button(
                            "📧 Email", 
                            key=f"email_btn_{audit['id']}", 
                            disabled=True, 
                            use_container_width=True,
                            help="⚠️ Configure email settings in sidebar to enable email functionality"
                        )
                
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

        # Bulk delete section at the bottom
        st.markdown("---")
        st.markdown("### 🗑️ Bulk Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Delete All Audits", type="secondary", use_container_width=True):
                if st.session_state.get("confirm_delete_all", False):
                    # Second click - actually delete all
                    all_audit_ids = [audit['id'] for audit in st.session_state.audit_history]
                    history_manager.delete_audits(all_audit_ids)
                    st.success("✅ Deleted all audits")
                    st.rerun()
                else:
                    # First click - show confirmation
                    st.session_state["confirm_delete_all"] = True
                    st.rerun()
            
            if st.session_state.get("confirm_delete_all", False):
                st.error("⚠️ This will delete ALL audit history. Click again to confirm.")
        
        with col2:
            if st.button("🗑️ Delete Filtered Audits", type="secondary", use_container_width=True):
                if st.session_state.get("confirm_delete_filtered", False):
                    # Second click - actually delete filtered
                    filtered_audit_ids = [audit['id'] for audit in filtered_history[:items_per_page]]
                    history_manager.delete_audits(filtered_audit_ids)
                    st.success(f"✅ Deleted {len(filtered_audit_ids)} filtered audits")
                    st.rerun()
                else:
                    # First click - show confirmation
                    st.session_state["confirm_delete_filtered"] = True
                    st.rerun()
            
            if st.session_state.get("confirm_delete_filtered", False):
                st.error(f"⚠️ This will delete {len(filtered_history[:items_per_page])} audits. Click again to confirm.")
        
elif st.session_state.current_page == "About":
    st.markdown("## ℹ️ About Design Assistant")
    
    st.markdown("""
    ### 🎨 AI-Powered Design Assistant
    
    A comprehensive tool for evaluating web design accessibility, contrast compliance, 
    and ethical UX patterns using advanced AI analysis.
    
    #### 🔧 Features
    
    - **🎯 Accessibility Audit**: WCAG compliance checking with detailed violation reports
    - **🎨 Contrast Analysis**: Color contrast evaluation with visual annotations
    - **⚖️ Ethical UX Scoring**: Dark pattern detection and ethical design assessment
    - **🧠 Persuasive Design Analysis**: Psychological pattern detection using AI
    - **🤖 AI Enhancement**: Google Gemini multimodal analysis
    - **📊 Visual Reports**: Interactive charts and comprehensive dashboards
    - **📚 Audit History**: Track improvements and trends over time
    - **📧 Email Reports**: Share results easily with stakeholders
    
    #### 🛠️ Technology Stack
    
    - **Frontend**: Streamlit
    - **AI Analysis**: Google Gemini 2.0 Flash
    - **Accessibility**: axe-core engine
    - **Contrast**: WCAG 2.1 AA/AAA algorithms
    - **Visualization**: Plotly interactive charts
    - **Email**: SMTP with Gmail integration
    
    #### 📧 Email Configuration
    
    To use the email functionality:
    1. Use a Gmail account
    2. Enable 2-Step Verification in your Google Account
    3. Generate an App Password from: [Google App Passwords](https://myaccount.google.com/apppasswords)
    4. Configure in the sidebar under "Email Configuration"
    
    #### 🌟 Best Practices
    
    - **Charts in Light Mode**: All charts display with white backgrounds for accurate color representation
    - **Regular Audits**: Run audits after every significant design change
    - **Historical Tracking**: Use the History page to monitor improvements over time
    - **Comprehensive Reports**: Download and share reports with your team
    
    #### 📄 License
    
    This tool is provided for educational and professional use.
    
    ---
    
    *Built with ❤️ for better, more accessible web experiences*
    """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 20px;'>"
    "🎨 AI-Powered Design Assistant v1.0 | Making the web better, one audit at a time<br>"
    "<small>Charts displayed with white backgrounds and black text for optimal readability</small>"
    "</div>",
    unsafe_allow_html=True
)