"""Theme management utilities"""
import streamlit as st

class ThemeManager:
    """Manage dark/light theme switching"""
    
    @staticmethod
    def get_theme_css(is_dark: bool) -> str:
        """Get CSS for current theme"""
        if is_dark:
            return """
            <style>
                .stApp {
                    background-color: #0e1117;
                    color: #fafafa;
                }
                .main .block-container {
                    background-color: #0e1117;
                    color: #fafafa;
                }
                .stSidebar {
                    background-color: #1a1d23;
                }
                .stRadio > div {
                    background-color: #262730;
                }
                .stButton > button {
                    color: #fafafa;
                    background-color: #262730;
                    border: 1px solid #555555;
                }
                .stTextInput > div > div > input {
                    background-color: #262730;
                    color: #fafafa;
                    border: 1px solid #555555;
                }
                .stSelectbox > div > div > select {
                    background-color: #262730;
                    color: #fafafa;
                }
                .stNumberInput > div > div > input {
                    background-color: #262730;
                    color: #fafafa;
                    border: 1px solid #555555;
                }
                .stSlider > div > div > div {
                    color: #fafafa;
                }
                .stExpander {
                    background-color: #262730;
                    border: 1px solid #555555;
                }
                .stDataFrame {
                    background-color: #262730;
                }
                .feature-card, .metric-card, .compact-config, .history-item {
                    background-color: #262730;
                    border: 1px solid #555555;
                    color: #fafafa;
                }
                /* Keep charts and visualizations in light mode for accuracy */
                .js-plotly-plot .plotly {
                    background-color: white !important;
                }
                /* Email popover */
                .email-popover {
                    background-color: #262730;
                    color: #fafafa;
                    border: 1px solid #555555;
                }
                /* Text color adjustments */
                p, h1, h2, h3, h4, h5, h6, span, div {
                    color: #fafafa;
                }
                /* Keep success/info boxes readable */
                .stSuccess, .stInfo, .stWarning, .stError {
                    color: #262730;
                }
            </style>
            """
        else:
            return """
            <style>
                .stApp {
                    background-color: #ffffff;
                    color: #262730;
                }
                .main .block-container {
                    background-color: #ffffff;
                    color: #262730;
                }
                .stSidebar {
                    background-color: #f8f9fa;
                }
                .feature-card, .metric-card, .compact-config, .history-item {
                    background-color: #ffffff;
                    border: 1px solid #e6e6e6;
                    color: #262730;
                }
                .email-popover {
                    background-color: white;
                    border: 1px solid #e6e6e6;
                }
            </style>
            """
    
    @staticmethod
    def apply_theme():
        """Apply current theme CSS"""
        is_dark = st.session_state.get('dark_mode', False)
        css = ThemeManager.get_theme_css(is_dark)
        st.markdown(css, unsafe_allow_html=True)