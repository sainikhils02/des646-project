"""Email configuration utilities"""
import os
import streamlit as st
from typing import Optional, Dict

class EmailConfig:
    """Manage email configuration"""
    
    @staticmethod
    def get_email_config() -> Optional[Dict]:
        """Get email configuration from environment or session state"""
        # Try environment variables first
        email_user = os.getenv("EMAIL_USER")
        email_password = os.getenv("EMAIL_PASSWORD")
        
        if email_user and email_password:
            return {
                "smtp_server": "smtp.gmail.com",
                "port": 587,
                "sender_email": email_user,
                "sender_password": email_password
            }
        
        # Try session state (user input)
        if 'email_config' in st.session_state:
            return st.session_state.email_config
            
        return None
    
    @staticmethod
    def setup_email_ui():
        """Show email configuration UI"""
        with st.expander("📧 Email Configuration"):
            st.info("To send emails, configure your SMTP settings below:")
            
            col1, col2 = st.columns(2)
            with col1:
                email_user = st.text_input(
                    "Email Address",
                    value=os.getenv("EMAIL_USER", ""),
                    placeholder="your-email@gmail.com"
                )
            with col2:
                email_password = st.text_input(
                    "App Password",
                    type="password",
                    value=os.getenv("EMAIL_PASSWORD", ""),
                    placeholder="Your app password",
                    help="For Gmail, use an App Password instead of your regular password"
                )
            
            smtp_server = st.text_input("SMTP Server", value="smtp.gmail.com")
            smtp_port = st.number_input("SMTP Port", value=587, min_value=1, max_value=9999)
            
            if st.button("Save Email Configuration"):
                if email_user and email_password:
                    st.session_state.email_config = {
                        "smtp_server": smtp_server,
                        "port": smtp_port,
                        "sender_email": email_user,
                        "sender_password": email_password
                    }
                    st.success("✅ Email configuration saved!")
                else:
                    st.error("Please fill in both email and password")
            
            return st.session_state.get('email_config')