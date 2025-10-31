"""Streamlit entry point for the AI-Powered Design Assistant."""
from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from design_assistant.pipeline import DesignAssistant, InputMode

# Try to import LLM support
try:
    from design_assistant.llm_integration import LLMConfig
    HAS_LLM_SUPPORT = True
except ImportError:
    HAS_LLM_SUPPORT = False
    LLMConfig = None


st.set_page_config(page_title="AI-Powered Design Assistant", layout="wide")

st.title("AI-Powered Design Assistant")
st.write(
    "Upload a screenshot or provide a URL to evaluate accessibility, contrast, and dark pattern risks."
)

output_dir = Path("outputs")

with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Scoring weights
    st.subheader("Score Weights")
    alpha = st.slider("Accessibility weight (α)", min_value=0.0, max_value=1.0, value=0.5)
    beta = st.slider("Ethical UX weight (β)", min_value=0.0, max_value=1.0, value=0.5)
    
    # LLM Configuration
    llm_config = None
    if HAS_LLM_SUPPORT:
        st.subheader("🤖 AI Enhancement (Optional)")
        use_llm = st.checkbox("Enable Gemini Multimodal Analysis", value=False)
        
        if use_llm:
            st.info("💡 Gemini analyzes screenshots and HTML for comprehensive insights. Requires Google AI API key.")
            
            api_key = st.text_input(
                "Google AI API Key",
                type="password",
                value=os.getenv("GOOGLE_API_KEY", ""),
                help="Your Google AI API key. Get one at aistudio.google.com/apikey"
            )
            
            model = st.selectbox(
                "Model",
                options=[
                    "models/gemini-2.5-pro",
                    "models/gemini-2.5-flash", 
                    "models/gemini-2.0-flash-exp",
                    "models/gemini-flash-latest"
                ],
                index=0,
                help="Gemini 2.5 Pro recommended for best multimodal analysis (vision + text)"
            )
            
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=0.7,
                help="Higher = more creative, Lower = more focused"
            )
            
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=1000,
                max_value=8000,
                value=8000,
                help="Maximum response length (higher for comprehensive analysis)"
            )
            
            if api_key:
                llm_config = LLMConfig(
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                st.success("✅ LLM enabled")
            else:
                st.warning("⚠️ Enter API key to enable LLM analysis")

# Create assistant with configuration
assistant = DesignAssistant(llm_config=llm_config, alpha=alpha, beta=beta)

mode = st.radio("Input mode", options=[InputMode.URL.value, InputMode.SCREENSHOT.value])

run_audit = False
uploaded_path: Path | None = None

if mode == InputMode.URL.value:
    url = st.text_input("URL", placeholder="https://example.com")
    if st.button("Run audit", disabled=not url):
        run_audit = True
else:
    upload = st.file_uploader("Screenshot", type=["png", "jpg", "jpeg", "webp"])
    if upload:
        uploaded_path = output_dir / upload.name
        uploaded_path.parent.mkdir(parents=True, exist_ok=True)
        uploaded_path.write_bytes(upload.getvalue())
    if st.button("Run audit", disabled=uploaded_path is None):
        run_audit = True

if run_audit:
    try:
        if mode == InputMode.URL.value:
            result = assistant.run(InputMode.URL, url, output_dir=output_dir)
        else:
            result = assistant.run(
                InputMode.SCREENSHOT,
                str(uploaded_path),
                output_dir=output_dir,
            )

        st.success(f"Design Fairness Score: {result.fairness.value:.2f}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Accessibility Score", result.accessibility.score if result.accessibility else 0.0)
            if result.accessibility:
                st.write(f"Violations: {len(result.accessibility.violations)}")
        with col2:
            st.metric("Average Contrast", f"{result.contrast.average_contrast:.2f}")
            st.write(f"Contrast Violations: {len(result.contrast.violations)}")
        with col3:
            st.metric("Ethical UX Score", f"{result.dark_patterns.score:.2f}")
            st.write(f"Dark Pattern Flags: {len(result.dark_patterns.flags)}")

        if result.contrast.violations:
            st.subheader("Contrast Violations")
            st.dataframe([violation.to_dict() for violation in result.contrast.violations])

        if result.dark_patterns.flags:
            st.subheader("Dark Pattern Flags")
            st.dataframe([flag.to_dict() for flag in result.dark_patterns.flags])

        if result.accessibility:
            st.subheader("Accessibility Violations")
            st.dataframe([violation.__dict__ for violation in result.accessibility.violations])

        # Display comprehensive report
        st.subheader("📊 Comprehensive Analysis Report")
        markdown_path = output_dir / "audit_report.md"
        if markdown_path.exists():
            report_content = markdown_path.read_text(encoding="utf-8")
            with st.expander("View Full Report", expanded=False):
                st.markdown(report_content)
        
        # Download buttons
        st.subheader("📥 Download Reports")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if markdown_path.exists():
                st.download_button(
                    "📄 Download Markdown Report",
                    data=markdown_path.read_bytes(),
                    file_name="audit_report.md",
                    mime="text/markdown",
                )
        
        with col2:
            json_path = output_dir / "audit.json"
            if json_path.exists():
                st.download_button(
                    "📋 Download JSON",
                    data=json_path.read_bytes(),
                    file_name="audit.json",
                    mime="application/json",
                )
        
        with col3:
            pdf_path = output_dir / "audit.pdf"
            if pdf_path.exists():
                st.download_button(
                    "📕 Download PDF Summary",
                    data=pdf_path.read_bytes(),
                    file_name="audit.pdf",
                    mime="application/pdf",
                )

    except Exception as exc:  # pragma: no cover - UI feedback
        st.error(f"Audit failed: {exc}")
