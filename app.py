import streamlit as st
import google.generativeai as genai
from PIL import Image
import sqlite3
import hashlib
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
import os

load_dotenv()
# 🔑 Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Email configuration from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Database setup
def init_database():
    conn = sqlite3.connect('codegpt_users.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  verified INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Chat history table
    c.execute('''CREATE TABLE IF NOT EXISTS chat_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  code_input TEXT,
                  features_used TEXT,
                  ai_output TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # OTP table
    c.execute('''CREATE TABLE IF NOT EXISTS otp_codes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT NOT NULL,
                  otp_code TEXT NOT NULL,
                  expires_at TIMESTAMP NOT NULL,
                  used INTEGER DEFAULT 0)''')
    
    conn.commit()
    conn.close()

# Initialize database
init_database()

# Utility functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(email, otp):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg['Subject'] = "CodeGPT - Email Verification Required"
        
        body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email Verification</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 300; letter-spacing: 1px;">
                        CodeGPT
                    </h1>
                    <p style="color: #e8eaf6; margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                        Email Verification
                    </p>
                </div>
                
                <!-- Content -->
                <div style="padding: 40px 30px;">
                    <h2 style="color: #333333; font-size: 24px; margin: 0 0 20px 0; font-weight: 400;">
                        Verify Your Email Address
                    </h2>
                    
                    <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                        To complete your registration and secure your account, please use the verification code below:
                    </p>
                    
                    <!-- OTP Box -->
                    <div style="background-color: #f8f9fa; border: 2px dashed #dee2e6; border-radius: 8px; padding: 30px; text-align: center; margin: 30px 0;">
                        <p style="color: #495057; font-size: 14px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                            Verification Code
                        </p>
                        <div style="font-size: 36px; font-weight: 700; color: #007bff; letter-spacing: 8px; font-family: 'Courier New', monospace;">
                            {otp}
                        </div>
                    </div>
                    
                    <!-- Important Info -->
                    <div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px 20px; margin: 30px 0; border-radius: 4px;">
                        <p style="color: #856404; font-size: 14px; margin: 0; line-height: 1.5;">
                            <strong>Important:</strong> This verification code will expire in 10 minutes for security purposes.
                        </p>
                    </div>
                    
                    <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 20px 0 0 0;">
                        If you didn't create an account with CodeGPT, you can safely ignore this email.
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8f9fa; padding: 30px; text-align: center; border-top: 1px solid #dee2e6;">
                    <p style="color: #6c757d; font-size: 14px; margin: 0 0 10px 0;">
                        This is an automated message from CodeGPT
                    </p>
                    <p style="color: #adb5bd; font-size: 12px; margin: 0;">
                        © 2025 CodeGPT. All rights reserved.
                    </p>
                </div>
                
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        text = msg.as_string()
        server.sendmail(EMAIL_USER, email, text)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Failed to send OTP: {str(e)}")
        return False

def store_otp(email, otp):
    conn = sqlite3.connect('codegpt_users.db')
    c = conn.cursor()
    expires_at = datetime.now() + timedelta(minutes=10)
    c.execute("INSERT INTO otp_codes (email, otp_code, expires_at) VALUES (?, ?, ?)",
              (email, otp, expires_at))
    conn.commit()
    conn.close()

def verify_otp(email, otp):
    conn = sqlite3.connect('codegpt_users.db')
    c = conn.cursor()
    c.execute("""SELECT id FROM otp_codes 
                 WHERE email = ? AND otp_code = ? AND expires_at > ? AND used = 0""",
              (email, otp, datetime.now()))
    result = c.fetchone()
    if result:
        c.execute("UPDATE otp_codes SET used = 1 WHERE id = ?", (result[0],))
        conn.commit()
    conn.close()
    return result is not None

# Page configuration
st.set_page_config(
    page_title="CodeGPT - AI Code Assistant", 
    page_icon="🧑‍💻",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern CSS styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&family=Poppins:wght@400;500;600;700;800&display=swap');
    
    /* Root variables for modern theme */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --accent-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --bg-primary: #0f0f23;
        --bg-secondary: rgba(255, 255, 255, 0.04);
        --bg-tertiary: rgba(255, 255, 255, 0.02);
        --text-primary: #ffffff;
        --text-secondary: #a8b2d1;
        --text-muted: #6b7280;
        --border-color: rgba(255, 255, 255, 0.08);
        --border-hover: rgba(102, 126, 234, 0.3);
        --hover-bg: rgba(255, 255, 255, 0.06);
        --shadow-light: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        --shadow-medium: 0 10px 25px -3px rgba(0, 0, 0, 0.1);
        --shadow-heavy: 0 20px 40px -12px rgba(0, 0, 0, 0.25);
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
    }
    
    /* Light theme - more refined */
    @media (prefers-color-scheme: light) {
        :root {
            --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            --accent-gradient: linear-gradient(135deg, #ec4899 0%, #f59e0b 100%);
            --bg-primary: #fafbff;
            --bg-secondary: rgba(79, 70, 229, 0.03);
            --bg-tertiary: rgba(0, 0, 0, 0.01);
            --text-primary: #1e1b4b;
            --text-secondary: #475569;
            --text-muted: #9ca3af;
            --border-color: rgba(79, 70, 229, 0.08);
            --border-hover: rgba(79, 70, 229, 0.2);
            --hover-bg: rgba(79, 70, 229, 0.04);
            --shadow-light: 0 4px 6px -1px rgba(79, 70, 229, 0.05);
            --shadow-medium: 0 10px 25px -3px rgba(79, 70, 229, 0.08);
            --shadow-heavy: 0 20px 40px -12px rgba(79, 70, 229, 0.12);
            --glass-bg: rgba(255, 255, 255, 0.7);
            --glass-border: rgba(79, 70, 229, 0.1);
        }
    }
    
    /* Force light theme */
    [data-theme="light"] {
        --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%) !important;
        --accent-gradient: linear-gradient(135deg, #ec4899 0%, #f59e0b 100%) !important;
        --bg-primary: #fafbff !important;
        --bg-secondary: rgba(79, 70, 229, 0.03) !important;
        --bg-tertiary: rgba(0, 0, 0, 0.01) !important;
        --text-primary: #1e1b4b !important;
        --text-secondary: #475569 !important;
        --text-muted: #9ca3af !important;
        --border-color: rgba(79, 70, 229, 0.08) !important;
        --border-hover: rgba(79, 70, 229, 0.2) !important;
        --hover-bg: rgba(79, 70, 229, 0.04) !important;
        --glass-bg: rgba(255, 255, 255, 0.7) !important;
        --glass-border: rgba(79, 70, 229, 0.1) !important;
    }
    
    /* Global Styles */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--bg-primary);
        color: var(--text-primary);
        min-height: 100vh;
        line-height: 1.6;
        font-weight: 400;
    }
    
    /* Hide default elements */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main container with better spacing */
    .main-container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 3rem 2rem;
    }
    
    /* Enhanced Header */
    .header {
        text-align: center;
        margin-bottom: 4rem;
        position: relative;
    }
    

    
    .header h1 {
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-family: 'Poppins', sans-serif;
        font-size: clamp(2.5rem, 5vw, 4.5rem);
        font-weight: 800;
        margin-bottom: 1.5rem;
        letter-spacing: -3px;
        line-height: 1.1;
    }
    
    .header p {
        color: var(--text-secondary);
        font-size: clamp(1rem, 2vw, 1.4rem);
        font-weight: 400;
        margin-bottom: 2rem;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    
    
    
    /* Enhanced Feature Cards */
    .feature-card {
        background: var(--glass-bg);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        backdrop-filter: blur(20px);
        position: relative;
        overflow: hidden;
    }
    
    .feature-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--primary-gradient);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }
    
    .feature-card:hover {
        background: var(--hover-bg);
        border-color: var(--border-hover);
        transform: translateY(-4px);
        box-shadow: var(--shadow-heavy);
    }
    
    .feature-card:hover::before {
        transform: scaleX(1);
    }
    
    .feature-card.selected {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        border-color: rgba(102, 126, 234, 0.4);
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.15);
        transform: translateY(-2px);
    }
    
    .feature-card.selected::before {
        transform: scaleX(1);
    }
    
    /* Modern Buttons */
    .stButton > button {
        width: 100%;
        background: var(--primary-gradient);
        color: white;
        border: none;
        border-radius: 16px;
        padding: 1.2rem 2.5rem;
        font-weight: 600;
        font-size: 1rem;
        font-family: 'Inter', sans-serif;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        text-transform: none;
        letter-spacing: 0.5px;
        box-shadow: var(--shadow-light);
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-heavy);
        filter: brightness(1.1);
    }
    
    .stButton > button:active {
        transform: translateY(-1px);
    }
    
    /* Enhanced Input Fields */
    .stTextInput > div > div > input, 
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select,
    .stNumberInput > div > div > input {
        background: var(--glass-bg) !important;
        border: 2px solid var(--border-color) !important;
        border-radius: 16px !important;
        color: var(--text-primary) !important;
        font-family: 'Inter', sans-serif !important;
        padding: 1.2rem 1.5rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-size: 1rem !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: var(--shadow-light) !important;
    }
    
    .stTextInput > div > div > input:focus, 
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--border-hover) !important;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1), var(--shadow-medium) !important;
        background: var(--hover-bg) !important;
        outline: none !important;
        transform: translateY(-2px) !important;
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: var(--text-muted) !important;
        opacity: 0.7 !important;
    }
    
    /* Enhanced Code Area */
    .stTextArea > div > div > textarea {
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 0.9rem !important;
        line-height: 1.7 !important;
        min-height: 350px !important;
        background: rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Modern Checkbox */
    .stCheckbox {
        margin: 1.5rem 0;
    }
    
    .stCheckbox > label {
        display: flex !important;
        align-items: center !important;
        font-size: 1.1rem !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
        padding: 1.5rem;
        background: var(--glass-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-light);
        position: relative;
        overflow: hidden;
    }
    
    .stCheckbox > label::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--accent-gradient);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }
    
    .stCheckbox > label:hover {
        background: var(--hover-bg);
        border-color: var(--border-hover);
        transform: translateY(-2px);
        box-shadow: var(--shadow-medium);
    }
    
    .stCheckbox > label:hover::before {
        transform: scaleX(1);
    }
    
    .stCheckbox input[type="checkbox"]:checked + label {
        background: linear-gradient(135deg, rgba(240, 147, 251, 0.1) 0%, rgba(245, 87, 108, 0.1) 100%);
        border-color: rgba(240, 147, 251, 0.4);
        color: var(--text-primary) !important;
        box-shadow: 0 10px 30px rgba(240, 147, 251, 0.2);
    }
    
    .stCheckbox input[type="checkbox"]:checked + label::before {
        transform: scaleX(1);
        background: var(--accent-gradient);
    }
    
    /* Enhanced Results Container */
    .result-container {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 3rem 0;
        backdrop-filter: blur(20px);
        width: 100%;
        box-sizing: border-box;
        box-shadow: var(--shadow-medium);
        transition: all 0.3s ease;
    }
    
    .result-container:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-heavy);
    }
    
    /* Modern Alert Boxes */
    .stSuccess, .stInfo, .stWarning, .stError {
        border-radius: 16px;
        border: none;
        backdrop-filter: blur(10px);
        margin: 1.5rem 0;
        padding: 1.5rem;
        box-shadow: var(--shadow-light);
        border-left: 4px solid;
    }
    
    .stSuccess {
        background: rgba(34, 197, 94, 0.1);
        border-left-color: #22c55e;
        color: var(--text-primary);
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.1);
        border-left-color: #3b82f6;
        color: var(--text-primary);
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.1);
        border-left-color: #f59e0b;
        color: var(--text-primary);
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.1);
        border-left-color: #ef4444;
        color: var(--text-primary);
    }
    
    /* Enhanced Chat History */
    .chat-history {
        background: var(--glass-bg);
        border: 1px solid var(--border-color);
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(10px);
        box-shadow: var(--shadow-light);
    }
    
    .chat-history:hover {
        background: var(--hover-bg);
        transform: translateY(-3px);
        box-shadow: var(--shadow-medium);
    }
    
    /* Modern Profile Card */
    .profile-card {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 3rem;
        text-align: center;
        backdrop-filter: blur(20px);
        box-shadow: var(--shadow-medium);
        transition: all 0.3s ease;
    }
    
    .profile-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-heavy);
    }
    
    /* Enhanced Expander */
    .streamlit-expanderHeader {
        background: var(--glass-bg) !important;
        border-radius: 16px !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: var(--shadow-light) !important;
        transition: all 0.3s ease !important;
    }
    
    .streamlit-expanderHeader:hover {
        background: var(--hover-bg) !important;
        border-color: var(--border-hover) !important;
    }
    
    .streamlit-expanderContent {
        background: var(--glass-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        color: var(--text-primary) !important;
        backdrop-filter: blur(10px) !important;
        margin-top: 0.5rem !important;
    }
    
    /* Modern File Uploader */
    .stFileUploader > div {
        background: var(--glass-bg) !important;
        border: 2px dashed var(--border-color) !important;
        border-radius: 20px !important;
        padding: 3rem !important;
        text-align: center !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        color: var(--text-primary) !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .stFileUploader > div:hover {
        border-color: var(--border-hover) !important;
        background: var(--hover-bg) !important;
        transform: translateY(-2px) !important;
    }
    
    /* Enhanced Form */
    .stForm {
        background: var(--glass-bg);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 2rem 0;
        backdrop-filter: blur(20px);
        box-shadow: var(--shadow-medium);
    }
    
    /* Modern Code Blocks */
    .stCode {
        background: rgba(0, 0, 0, 0.9) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 16px !important;
        color: #ffffff !important;
        font-family: 'JetBrains Mono', monospace !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: var(--shadow-light) !important;
    }
    
    /* Typography Enhancements */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
        color: var(--text-primary) !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        line-height: 1.3 !important;
    }
    
    .stMarkdown p, .stMarkdown li, .stMarkdown span {
        color: var(--text-primary) !important;
        line-height: 1.7 !important;
    }
    
    .stMarkdown strong {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-tertiary);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary-gradient);
        border-radius: 10px;
        border: 2px solid var(--bg-primary);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--accent-gradient);
    }
    
    /* Enhanced Footer */
    .footer {
        margin-top: 6rem;
        padding: 3rem 2rem;
        text-align: center;
        background: var(--glass-bg);
        border-top: 1px solid var(--glass-border);
        color: var(--text-secondary);
        backdrop-filter: blur(20px);
        border-radius: 24px 24px 0 0;
    }
    
    .footer p {
        margin: 0.8rem 0;
        color: var(--text-secondary) !important;
        line-height: 1.6;
    }
    
    .footer strong {
        color: var(--text-primary) !important;
        font-weight: 600;
    }
    
    /* Responsive Design */
    @media (max-width: 1024px) {
        .main-container {
            max-width: 100%;
            padding: 2rem 1.5rem;
        }
    }
    
    @media (max-width: 768px) {
        .header h1 {
            font-size: 2.5rem;
            letter-spacing: -1px;
        }
        
        .header p {
            font-size: 1.1rem;
        }
        
        .main-container {
            padding: 1.5rem 1rem;
        }
        
        .stCheckbox > label {
            font-size: 1rem !important;
            padding: 1.2rem;
        }
        
        .feature-card {
            padding: 1.5rem;
        }
        
        .result-container {
            padding: 2rem;
        }
    }
    
    @media (max-width: 480px) {
        .header {
            margin-bottom: 2rem;
        }
        
        .nav-container {
            padding: 1rem;
        }
        
        .stButton > button {
            padding: 1rem 2rem;
        }
    }
    
    /* Modern Animations */
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    
    @keyframes pulse {
        0%, 100% { 
            opacity: 1; 
            transform: scale(1);
        }
        50% { 
            opacity: 0.8; 
            transform: scale(1.02);
        }
    }
    
    .loading {
        animation: pulse 2s infinite;
    }
    
    .fade-in {
        animation: fadeIn 0.6s ease-out;
    }
    
    .slide-in-up {
        animation: slideInUp 0.6s ease-out;
    }
    
    /* Performance optimizations */
    * {
        box-sizing: border-box;
    }
    
    body {
        overflow-x: hidden;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    .main {
        padding-bottom: 0 !important;
    }
    
    /* Focus states for accessibility */
    button:focus-visible,
    input:focus-visible,
    textarea:focus-visible,
    select:focus-visible {
        outline: 2px solid rgba(102, 126, 234, 0.6);
        outline-offset: 2px;
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        :root {
            --border-color: rgba(255, 255, 255, 0.3);
            --text-secondary: #e5e5e5;
        }
    }
    
    /* Reduced motion support */
    @media (prefers-reduced-motion: reduce) {
        * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'main'
if 'temp_email' not in st.session_state:
    st.session_state.temp_email = None
if 'temp_username' not in st.session_state:
    st.session_state.temp_username = None
if 'temp_password' not in st.session_state:
    st.session_state.temp_password = None

# Professional Navigation
def show_navigation():
    col1, col2, col3, col4, col5, col6 = st.columns([1,1,1,1,1,1])
    
    with col1:
        if st.button("🏠 Home", key="nav_home"):
            st.session_state.current_page = 'main'
            st.rerun()
    
    with col2:
        if st.button("📊 History", key="nav_history"):
            if st.session_state.authenticated:
                st.session_state.current_page = 'history'
                st.rerun()
            else:
                st.warning("Please login to view history")
    
    with col3:
        if not st.session_state.authenticated:
            if st.button("🔐 Login", key="nav_login"):
                st.session_state.current_page = 'login'
                st.rerun()
        else:
            if st.button("👤 Profile", key="nav_profile"):
                st.session_state.current_page = 'profile'
                st.rerun()
    
    with col4:
        if not st.session_state.authenticated:
            if st.button("📝 Sign Up", key="nav_signup"):
                st.session_state.current_page = 'signup'
                st.rerun()
        else:
            if st.button("🚪 Logout", key="nav_logout"):
                st.session_state.authenticated = False
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.current_page = 'main'
                st.success("Logged out successfully!")
                st.rerun()
    
    with col5:
        if st.button("ℹ About", key="nav_about"):
            st.session_state.current_page = 'about'
            st.rerun()

    with col6:
        if st.button("📞 Contact", key="nav_contact"):
            st.session_state.current_page = 'contact'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

# Authentication functions


# Authentication functions
def signup_page():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.markdown("## 📝 Create Account")
    
    with st.form("signup_form"):
        username = st.text_input("Username", placeholder="Enter username")
        email = st.text_input("Email", placeholder="Enter email address")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password")
        
        submitted = st.form_submit_button("Create Account")

        
        if submitted:
            if not all([username, email, password, confirm_password]):
                st.error("Please fill all fields")
            elif password != confirm_password:
                st.error("Passwords don't match")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            else:
                # Check if user exists
                conn = sqlite3.connect('codegpt_users.db')
                c = conn.cursor()
                c.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
                if c.fetchone():
                    st.error("Username or email already exists")
                    conn.close()
                else:
                    conn.close()
                    # Generate and send OTP
                    otp = generate_otp()
                    if send_otp_email(email, otp):
                        store_otp(email, otp)
                        st.session_state.temp_username = username
                        st.session_state.temp_email = email
                        st.session_state.temp_password = hash_password(password)
                        st.session_state.current_page = 'verify_otp'
                        st.success("OTP sent to your email! Check your inbox.")
                        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style='text-align: center;'>
                <p>Already have an account?</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        if st.button("🔐 Login Here", key="signup_to_login", use_container_width=True):
            st.session_state.current_page = 'login'
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def contactus():    
    # Contact Form Section
    st.header("📝 Send us a Message")
    
    with st.form("contact_form"):
        # Form fields
        name = st.text_input("Full Name *", placeholder="Enter your full name")
        email = st.text_input("Email Address *", placeholder="Enter your email address")
        
        col1, col2 = st.columns(2)
        with col1:
            subject_type = st.selectbox(
                "Subject Category *",
                ["General Inquiry", "Technical Support", "Bug Report", "Feature Request", "Billing", "Other"]
            )
        with col2:
            priority = st.selectbox(
                "Priority Level",
                ["Low", "Medium", "High", "Urgent"]
            )
        
        subject = st.text_input("Subject *", placeholder="Brief description of your inquiry")
        message = st.text_area(
            "Message *", 
            placeholder="Please provide detailed information about your inquiry...",
            height=150
        )
        
        # Additional options
        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input("Phone Number (Optional)", placeholder="For urgent matters")
        with col2:
            preferred_contact = st.selectbox(
                "Preferred Contact Method",
                ["Email", "Phone", "No Preference"]
            )
        
        # File upload for attachments
        uploaded_file = st.file_uploader(
            "Attach Files (Optional)",
            type=['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg'],
            help="Upload any relevant documents or screenshots"
        )
        
        # Newsletter signup
        newsletter = st.checkbox("Subscribe to our newsletter for updates and tips")
        
        # Submit button
        submitted = st.form_submit_button("📤 Send Message", use_container_width=True)
        
        if submitted:
            # Validation
            if not name or not email or not subject or not message:
                st.error("Please fill in all required fields marked with *")
            elif "@" not in email or "." not in email:
                st.error("Please enter a valid email address")
            else:
                # Here you would typically save to database or send email
                # For now, we'll just show a success message
                st.success("✅ Thank you for contacting us!")
                st.info(f"We've received your message about '{subject}' and will respond within 24 hours.")
                
                # You can add code here to:
                # 1. Save to database
                # 2. Send email notification
                # 3. Create support ticket
                
                # Example of what you might store:
                contact_data = {
                    "name": name,
                    "email": email,
                    "subject_type": subject_type,
                    "priority": priority,
                    "subject": subject,
                    "message": message,
                    "phone": phone,
                    "preferred_contact": preferred_contact,
                    "newsletter": newsletter,
                    "timestamp": "datetime.now()",
                    "file_attached": uploaded_file is not None
                }
                
                # Clear form (optional - Streamlit will handle this on rerun)
                st.balloons()
    
    st.markdown("---")
    
    # Contact Information Section
    st.header("Get in Touch")
    st.write("We'd love to hear from you! Reach out to us using any of the methods below:")
    
    col1, col2 ,col3, col4= st.columns(4)
    
    with col1:
        st.subheader("📧 Email")
        st.write("support@codegpt.com")
        st.write("info@codegpt.com")
        
        st.subheader("📱 Phone")
        st.write("+1 (555) 123-4567")
        st.write("Mon-Fri: 9:00 AM - 6:00 PM IST")
        
    with col2:
        st.subheader("🌐 Social Media")
        st.write("Follow us on:")
        st.write("• Twitter: @codegptapp")
        st.write("• LinkedIn: codegpt")
        st.write("• Facebook: codegpt")
    with col3:
        st.subheader("📍 Address")
        st.write("Sri sainath nagar")
        st.write("Rangampeta")
        st.write("Tirupati, Andhrapradesh 12345")
    
    with col4:
        st.subheader("⏰ Response Time")
        st.write("• Email: Within 24 hours")
        st.write("• Phone: Immediate")
        st.write("• Support tickets: Within 4 hours")
    
    st.markdown("---")
    
    # FAQ Section
    st.header("❓ Frequently Asked Questions")
    
    with st.expander("How quickly will I receive a response?"):
        st.write("We typically respond to emails within 24 hours during business days. For urgent matters, please call our phone number directly.")
    
    with st.expander("What information should I include in my message?"):
        st.write("Please include as much detail as possible about your issue or inquiry. Screenshots, error messages, and step-by-step descriptions help us assist you better.")
    
    with st.expander("Do you offer phone support?"):
        st.write("Yes! Our phone support is available Monday through Friday, 9:00 AM to 6:00 PM EST. For technical issues, email support may be more effective as we can share screenshots and detailed instructions.")
    
    with st.expander("Can I schedule a demo or consultation?"):
        st.write("Absolutely! Please select 'General Inquiry' as your subject category and mention that you'd like to schedule a demo. We'll get back to you with available time slots.")
    
    # Back to main page
    if st.button("← Back to Home", key="contact_back_home"):
        st.session_state.current_page = 'main'
        st.rerun()

def verify_otp_page():
    st.markdown("### 📧 Verify Email")
    st.info(f"OTP sent to: {st.session_state.temp_email}")
    
    with st.form("otp_form"):
        otp_input = st.text_input("Enter OTP", placeholder="Enter 6-digit OTP")
        submitted = st.form_submit_button("Verify")
        
        if submitted:
            if verify_otp(st.session_state.temp_email, otp_input):
                # Create user account
                conn = sqlite3.connect('codegpt_users.db')
                c = conn.cursor()
                c.execute("INSERT INTO users (username, email, password_hash, verified) VALUES (?, ?, ?, 1)",
                         (st.session_state.temp_username, st.session_state.temp_email, st.session_state.temp_password))
                conn.commit()
                conn.close()
                
                st.success("Account created successfully! Please login.")
                st.session_state.current_page = 'login'
                st.session_state.temp_email = None
                st.session_state.temp_username = None
                st.session_state.temp_password = None
                st.rerun()
            else:
                st.error("Invalid or expired OTP")
    
    if st.button("← Back to Signup"):
        st.session_state.current_page = 'signup'
        st.rerun()
    

def login_page():
    st.markdown("### 🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username or Email", placeholder="Enter username or email")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if username and password:
                conn = sqlite3.connect('codegpt_users.db')
                c = conn.cursor()
                c.execute("SELECT id, username, verified FROM users WHERE (username = ? OR email = ?) AND password_hash = ?",
                         (username, username, hash_password(password)))
                user = c.fetchone()
                conn.close()
                
                if user:
                    if user[2]:  # verified
                        st.session_state.authenticated = True
                        st.session_state.user_id = user[0]
                        st.session_state.username = user[1]
                        st.session_state.current_page = 'main'
                        st.success(f"Welcome back, {user[1]}!")
                        st.rerun()
                    else:
                        st.error("Please verify your email first")
                else:
                    st.error("Invalid credentials")
            else:
                st.error("Please fill all fields")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style='text-align: center;'>
                <p>Don't have an account?</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        if st.button("📝 Sign Up Here", key="login_to_signup", use_container_width=True):
            st.session_state.current_page = 'signup'
            st.rerun()

def profile_page():
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.markdown("## 👤 Profile")
    
    if st.session_state.authenticated:
        conn = sqlite3.connect('codegpt_users.db')
        c = conn.cursor()
        c.execute("SELECT username, email, created_at FROM users WHERE id = ?", (st.session_state.user_id,))
        user_data = c.fetchone()
        
        # Get chat history count
        c.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (st.session_state.user_id,))
        chat_count = c.fetchone()[0]
        conn.close()
        
        if user_data:
            # Profile Display Section
            st.markdown("""
            <div class="profile-card">
                <h3 style="text-align: center; margin-bottom: 2rem;">🎯 User Profile</h3>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class="feature-card">
                    <h4>👤 Account Information</h4>
                    <p><strong>Username:</strong> {user_data[0]}</p>
                    <p><strong>Email:</strong> {user_data[1]}</p>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown(f"""
                <div class="feature-card">
                    <h4>📊 Activity Stats</h4>
                    <p><strong>Member Since:</strong> {user_data[2][:10]}</p>
                    <p><strong>Total Analyses:</strong> {chat_count}</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Edit Profile Section
            st.markdown("---")
            st.markdown("### ✏️ Edit Profile")
            
            with st.form("edit_profile_form"):
                st.markdown("**Update your profile information:**")
                new_username = st.text_input("New Username", value=user_data[0], placeholder="Enter new username")
                new_email = st.text_input("New Email", value=user_data[1], placeholder="Enter new email")
                
                col1, col2 = st.columns(2)
                with col1:
                    current_password = st.text_input("Current Password", type="password", placeholder="Enter current password")
                with col2:
                    new_password = st.text_input("New Password (optional)", type="password", placeholder="Enter new password")
                
                submitted = st.form_submit_button("💾 Update Profile", type="primary")
                
                if submitted:
                    if not current_password:
                        st.error("Please enter your current password to make changes")
                    else:
                        # Verify current password
                        conn = sqlite3.connect('codegpt_users.db')
                        c = conn.cursor()
                        c.execute("SELECT password_hash FROM users WHERE id = ?", (st.session_state.user_id,))
                        stored_password = c.fetchone()[0]
                        
                        if hash_password(current_password) == stored_password:
                            # Update profile
                            if new_password:
                                # Update with new password
                                c.execute("UPDATE users SET username = ?, email = ?, password_hash = ? WHERE id = ?",
                                         (new_username, new_email, hash_password(new_password), st.session_state.user_id))
                            else:
                                # Update without password change
                                c.execute("UPDATE users SET username = ?, email = ? WHERE id = ?",
                                         (new_username, new_email, st.session_state.user_id))
                            
                            conn.commit()
                            conn.close()
                            
                            # Update session state
                            st.session_state.username = new_username
                            st.success("✅ Profile updated successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Current password is incorrect")
                            conn.close()
    
    st.markdown('</div>', unsafe_allow_html=True)


def history_page():
    
    # Enhanced Header
    st.markdown("""
    <div class="header">
        <h1>📊 Analysis History</h1>
        <p>Track your coding journey and past analyses</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.authenticated:
        conn = sqlite3.connect('codegpt_users.db')
        c = conn.cursor()
        
        # Get total count for pagination
        c.execute("SELECT COUNT(*) FROM chat_history WHERE user_id = ?", (st.session_state.user_id,))
        total_count = c.fetchone()[0]
        
        # Pagination controls
        items_per_page = 10
        total_pages = (total_count + items_per_page - 1) // items_per_page
        
        if 'current_page_num' not in st.session_state:
            st.session_state.current_page_num = 1
        
        # Stats overview
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="feature-card" style="text-align: center;">
                <h3 style="color: #667eea;">📈</h3>
                <h4>{total_count}</h4>
                <p>Total Analyses</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Get this week's count
            c.execute("""SELECT COUNT(*) FROM chat_history 
                        WHERE user_id = ? AND created_at >= date('now', '-7 days')""", 
                     (st.session_state.user_id,))
            week_count = c.fetchone()[0]
            st.markdown(f"""
            <div class="feature-card" style="text-align: center;">
                <h3 style="color: #22c55e;">📅</h3>
                <h4>{week_count}</h4>
                <p>This Week</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Most used feature
            c.execute("""SELECT features_used, COUNT(*) as count 
                        FROM chat_history WHERE user_id = ? 
                        GROUP BY features_used ORDER BY count DESC LIMIT 1""", 
                     (st.session_state.user_id,))
            popular_feature = c.fetchone()
            feature_name = popular_feature[0].split(',')[0] if popular_feature else "None"
            st.markdown(f"""
            <div class="feature-card" style="text-align: center;">
                <h3 style="color: #f59e0b;">⭐</h3>
                <h4>{feature_name}</h4>
                <p>Most Used</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            # Average per week
            avg_per_week = max(1, total_count // 4) if total_count > 0 else 0
            st.markdown(f"""
            <div class="feature-card" style="text-align: center;">
                <h3 style="color: #ec4899;">📊</h3>
                <h4>{avg_per_week}</h4>
                <p>Avg/Week</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Pagination controls
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button("⬅️ Previous", disabled=(st.session_state.current_page_num <= 1)):
                    st.session_state.current_page_num -= 1
                    st.rerun()
            
            with col2:
                st.markdown(f"<h4 style='text-align: center;'>Page {st.session_state.current_page_num} of {total_pages}</h4>", 
                           unsafe_allow_html=True)
            
            with col3:
                if st.button("Next ➡️", disabled=(st.session_state.current_page_num >= total_pages)):
                    st.session_state.current_page_num += 1
                    st.rerun()
        
        # Get paginated history
        offset = (st.session_state.current_page_num - 1) * items_per_page
        c.execute("""SELECT code_input, features_used, ai_output, created_at 
                     FROM chat_history WHERE user_id = ? 
                     ORDER BY created_at DESC LIMIT ? OFFSET ?""", 
                 (st.session_state.user_id, items_per_page, offset))
        history = c.fetchall()
        conn.close()
        
        if history:
            st.markdown("### 📋 Recent Analyses")
            
            for i, (code, features, output, timestamp) in enumerate(history):
                # Enhanced history card design
                analysis_num = offset + i + 1
                date_formatted = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y at %I:%M %p")
                
                # Feature badges
                feature_list = features.split(',')
                feature_badges = ""
                for feature in feature_list[:3]:  # Show first 3 features
                    color = "#667eea" if "Bug" in feature else "#22c55e" if "Explain" in feature else "#f59e0b"
                    feature_badges += f'<span style="background: {color}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8rem; margin-right: 8px;">{feature.strip()}</span>'
                
                if len(feature_list) > 3:
                    feature_badges += f'<span style="background: #6b7280; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8rem;">+{len(feature_list)-3} more</span>'
                
                # Create expandable card
                with st.expander(f"🔍 Analysis #{analysis_num} • {date_formatted}", expanded=False):
                    st.markdown(f"""
                    <div class="chat-history">
                        <div style="margin-bottom: 1.5rem;">
                            <h4 style="margin-bottom: 0.5rem;">🏷️ Features Used:</h4>
                            <div style="margin-bottom: 1rem;">{feature_badges}</div>
                        </div>
                        
                       
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show code with syntax highlighting
                    code_preview = code[:400] + "..." if len(code) > 400 else code
                    st.code(code_preview, language='python')
                    
                    st.markdown("**🤖 AI Analysis Preview:**")
                    output_preview = output[:500] + "..." if len(output) > 500 else output
                    st.markdown(output_preview)
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"📋 Copy Code", key=f"copy_{analysis_num}"):
                            st.success("Code copied to clipboard!")
                    with col2:
                        if st.button(f"🔄 Re-analyze", key=f"reanalyze_{analysis_num}"):
                            st.session_state.current_page = 'main'
                            st.info("Redirecting to main page...")
                            st.rerun()
                    with col3:
                        if st.button(f"📊 Full View", key=f"expand_{analysis_num}"):
                            st.markdown("**Complete Analysis:**")
                            st.markdown(output)
        else:
            st.markdown("""
            <div class="feature-card" style="text-align: center; padding: 3rem;">
                <h3>📭 No Analysis History</h3>
                <p>Start using CodeGPT to see your analysis history here!</p>
                <br>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🚀 Start Analyzing", type="primary"):
                st.session_state.current_page = 'main'
                st.rerun()
    else:
        st.markdown("""
        <div class="feature-card" style="text-align: center; padding: 3rem;">
            <h3>🔐 Login Required</h3>
            <p>Please login to view your analysis history</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,1,1])
        with col2:
            if st.button("🔐 Login Now", type="primary"):
                st.session_state.current_page = 'login'
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def about_page():
    # Enhanced CSS with proper alignment and dark theme support
    st.markdown("""
    <style>
    /* Root variables for theme support */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
        --bg-light: #ffffff;
        --bg-dark: #1a202c;
        --text-primary-light: #2d3748;
        --text-primary-dark: #f7fafc;
        --text-secondary-light: #4a5568;
        --text-secondary-dark: #cbd5e0;
        --card-bg-light: #ffffff;
        --card-bg-dark: #2d3748;
        --border-light: #e2e8f0;
        --border-dark: #4a5568;
        --section-bg-light: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        --section-bg-dark: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
    }
    
    /* Dark theme detection */
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-primary: var(--bg-dark);
            --text-primary: var(--text-primary-dark);
            --text-secondary: var(--text-secondary-dark);
            --card-bg: var(--card-bg-dark);
            --border-color: var(--border-dark);
            --section-bg: var(--section-bg-dark);
        }
    }
    
    @media (prefers-color-scheme: light) {
        :root {
            --bg-primary: var(--bg-light);
            --text-primary: var(--text-primary-light);
            --text-secondary: var(--text-secondary-light);
            --card-bg: var(--card-bg-light);
            --border-color: var(--border-light);
            --section-bg: var(--section-bg-light);
        }
    }
    
    /* Streamlit dark theme override */
    .stApp[data-theme="dark"] {
        --bg-primary: var(--bg-dark);
        --text-primary: var(--text-primary-dark);
        --text-secondary: var(--text-secondary-dark);
        --card-bg: var(--card-bg-dark);
        --border-color: var(--border-dark);
        --section-bg: var(--section-bg-dark);
    }
    
    .stApp[data-theme="light"] {
        --bg-primary: var(--bg-light);
        --text-primary: var(--text-primary-light);
        --text-secondary: var(--text-secondary-light);
        --card-bg: var(--card-bg-light);
        --border-color: var(--border-light);
        --section-bg: var(--section-bg-light);
    }
    
    /* Main wrapper with proper alignment */
    .about-main-wrapper {
        max-width: 1400px;
        margin: 0 auto;
        padding: 2rem;
        font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        width: 100%;
        box-sizing: border-box;
    }
    
    /* Hero banner with enhanced styling */
    .about-hero-banner {
        background: var(--primary-gradient);
        color: white;
        padding: 4rem 2rem;
        border-radius: 24px;
        text-align: center;
        margin-bottom: 4rem;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .about-hero-banner::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="50" cy="50" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
        pointer-events: none;
    }
    
    .about-hero-banner h1 {
        font-size: clamp(2.5rem, 5vw, 4rem) !important;
        font-weight: 800 !important;
        margin-bottom: 1.5rem !important;
        color: white !important;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
    }
    
    .about-hero-banner p {
        font-size: clamp(1.1rem, 2vw, 1.4rem) !important;
        opacity: 0.95 !important;
        max-width: 800px !important;
        margin: 0 auto !important;
        line-height: 1.8 !important;
        color: white !important;
        position: relative;
        z-index: 1;
    }
    
    /* Features section with better alignment */
    .about-features-section {
        margin: 5rem 0;
        width: 100%;
    }
    
    .about-features-header {
        text-align: center;
        margin-bottom: 4rem;
    }
    
    .about-features-header h2 {
        font-size: clamp(2rem, 4vw, 3rem) !important;
        color: var(--text-primary) !important;
        margin-bottom: 1rem !important;
        font-weight: 700 !important;
    }
    
    .about-features-header p {
        font-size: 1.2rem !important;
        color: var(--text-secondary) !important;
        max-width: 600px !important;
        margin: 0 auto !important;
        line-height: 1.6 !important;
    }
    
    /* Grid layout for features - 3 columns */
    .about-features-container {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 2rem;
        width: 100%;
        max-width: 1300px;
        margin: 0 auto;
        padding: 0 1rem;
    }
    
    .about-feature-box {
        background: var(--card-bg);
        padding: 2.5rem 1.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        border: 2px solid var(--border-color);
        text-align: center;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        min-height: 300px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    
    .about-feature-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: var(--primary-gradient);
        opacity: 0;
        transition: opacity 0.4s ease;
        z-index: 0;
    }
    
    .about-feature-box:hover::before {
        opacity: 0.05;
    }
    
    .about-feature-box:hover {
        transform: translateY(-12px) scale(1.02);
        box-shadow: 0 25px 50px rgba(102, 126, 234, 0.2);
        border-color: #667eea;
    }
    
    .about-feature-emoji {
        font-size: 3.5rem;
        display: block;
        margin-bottom: 1.5rem;
        filter: drop-shadow(0 4px 12px rgba(0,0,0,0.1));
        position: relative;
        z-index: 1;
    }
    
    .about-feature-box h3 {
        color: var(--text-primary) !important;
        font-size: 1.4rem !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
        line-height: 1.4 !important;
        position: relative;
        z-index: 1;
    }
    
    .about-feature-box p {
        color: var(--text-secondary) !important;
        font-size: 1rem !important;
        line-height: 1.6 !important;
        margin: 0 !important;
        position: relative;
        z-index: 1;
        flex-grow: 1;
    }
    
    /* Technology section with proper theming */
    .about-tech-section {
        background: var(--section-bg);
        padding: 4rem 2rem;
        border-radius: 24px;
        margin: 5rem 0;
        text-align: center;
        border: 2px solid var(--border-color);
    }
    
    .about-tech-section h2 {
        color: var(--text-primary) !important;
        font-size: clamp(1.8rem, 3vw, 2.5rem) !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
    }
    
    .about-tech-section > p {
        color: var(--text-secondary) !important;
        font-size: 1.2rem !important;
        margin-bottom: 2rem !important;
    }
    
    .about-tech-tags {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 1rem;
        margin-top: 2rem;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .about-tech-tag {
        background: var(--card-bg);
        padding: 1rem 2rem;
        border-radius: 50px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        border: 2px solid var(--border-color);
        font-weight: 600;
        color: var(--text-primary);
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: default;
        white-space: nowrap;
    }
    
    .about-tech-tag:hover {
        background: var(--primary-gradient);
        color: white !important;
        transform: translateY(-4px) scale(1.05);
        box-shadow: 0 12px 30px rgba(102, 126, 234, 0.4);
        border-color: transparent;
    }
    
    /* Statistics grid with improved spacing */
    .about-stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 2rem;
        margin: 4rem 0;
        padding: 2rem 0;
        max-width: 2000px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .about-stat-card {
        text-align: center;
        padding: 2.5rem 1.5rem;
        background: var(--card-bg);
        border-radius: 20px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        border: 2px solid var(--border-color);
        transition: all 0.3s ease;
    }
    
    .about-stat-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.15);
    }
    
    .about-stat-number {
        font-size: clamp(2.5rem, 4vw, 3.5rem) !important;
        font-weight: 800 !important;
        color: #667eea !important;
        display: block !important;
        margin-bottom: 1rem !important;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .about-stat-label {
        color: var(--text-secondary) !important;
        font-size: 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        font-weight: 600 !important;
        line-height: 1.4 !important;
    }
    
    /* Call to action with enhanced styling */
    .about-cta-banner {
        background: var(--primary-gradient);
        color: white;
        padding: 4rem 2rem;
        border-radius: 24px;
        text-align: center;
        margin-top: 5rem;
        box-shadow: 0 15px 40px rgba(66, 153, 225, 0.4);
        position: relative;
        overflow: hidden;
    }
    
    .about-cta-banner::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="10" cy="10" r="1" fill="white" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23dots)"/></svg>');
        pointer-events: none;
    }
    
    .about-cta-banner h2 {
        font-size: clamp(1.8rem, 3vw, 2.5rem) !important;
        font-weight: 700 !important;
        margin-bottom: 1.5rem !important;
        color: white !important;
        position: relative;
        z-index: 1;
    }
    
    .about-cta-banner p {
        font-size: clamp(1rem, 2vw, 1.3rem) !important;
        opacity: 0.95 !important;
        margin-bottom: 0 !important;
        color: white !important;
        max-width: 700px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        line-height: 1.6 !important;
        position: relative;
        z-index: 1;
    }
    
    /* Responsive design improvements */
    @media (max-width: 1200px) {
        .about-main-wrapper {
            padding: 1.5rem;
        }
        
        .about-features-container {
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
        }
    }
    
    @media (max-width: 768px) {
        .about-main-wrapper {
            padding: 1rem;
        }
        
        .about-features-container {
            grid-template-columns: 1fr;
            gap: 1.5rem;
            padding: 0;
        }
        
        .about-feature-box {
            padding: 2rem 1.5rem;
            min-height: auto;
        }
        
        .about-hero-banner {
            padding: 3rem 1.5rem;
            margin-bottom: 3rem;
        }
        
        .about-tech-section {
            padding: 3rem 1.5rem;
        }
        
        .about-tech-tags {
            gap: 0.75rem;
        }
        
        .about-tech-tag {
            padding: 0.75rem 1.5rem;
            font-size: 0.9rem;
        }
        
        .about-stats-grid {
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
        }
        
        .about-stat-card {
            padding: 2rem 1rem;
        }
        
        .about-cta-banner {
            padding: 3rem 1.5rem;
        }
    }
    
    @media (max-width: 480px) {
        .about-features-container {
            grid-template-columns: 1fr;
            padding: 0;
        }
        
        .about-feature-box {
            margin: 0;
            padding: 1.5rem;
        }
        
        .about-tech-tags {
            gap: 0.5rem;
        }
        
        .about-tech-tag {
            padding: 0.6rem 1.2rem;
            font-size: 0.85rem;
        }
        
        .about-stats-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main container
    st.markdown('<div class="about-main-wrapper">', unsafe_allow_html=True)
    
    # Hero Section
    st.markdown("""
    <div class="about-hero-banner">
        <h1>🚀 CodeGPT</h1>
        <p>Your intelligent AI-powered coding companion that transforms the way you write, debug, and optimize code across multiple programming languages with cutting-edge technology.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Features Section
    st.markdown('<div class="about-features-section">', unsafe_allow_html=True)
    st.markdown('''
    <div class="about-features-header">
        <h2>Powerful Features</h2>
        <p>Discover the comprehensive set of tools designed to enhance your coding experience and productivity.</p>
    </div>
    ''', unsafe_allow_html=True)
    
    # Features Grid
    st.markdown('<div class="about-features-container">', unsafe_allow_html=True)
    
    # Feature boxes
    features = [
        {
            "emoji": "🐛",
            "title": "Bug Detection & Fixing",
            "description": "Instantly identify and resolve bugs in your code with AI-powered analysis and intelligent suggested fixes that save you hours of debugging time."
        },
        {
            "emoji": "📚",
            "title": "Code Explanation",
            "description": "Get detailed, step-by-step explanations of complex code snippets and understand algorithms with clear, beginner-friendly descriptions."
        },
        {
            "emoji": "📸",
            "title": "Handwritten Code Recognition",
            "description": "Upload images of handwritten code and convert them to digital format with high accuracy using advanced OCR technology."
        },
        {
            "emoji": "⚡",
            "title": "Code Optimization",
            "description": "Improve your code performance with intelligent optimization suggestions, best practices, and efficiency improvements."
        },
        {
            "emoji": "🌍",
            "title": "Multi-language Support",
            "description": "Work seamlessly with Python, JavaScript, Java, C++, Go, Rust, and 50+ other programming languages and frameworks."
        },
        {
            "emoji": "🔄",
            "title": "Code Refactoring",
            "description": "Transform legacy code into modern, maintainable, and efficient solutions automatically with smart refactoring suggestions."
        }
    ]
    
    for feature in features:
        st.markdown(f"""
        <div class="about-feature-box">
            <span class="about-feature-emoji">{feature['emoji']}</span>
            <h3>{feature['title']}</h3>
            <p>{feature['description']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div></div>', unsafe_allow_html=True)  # Close features container and section
    
    # Technology Stack Section
    st.markdown('''
    <div class="about-tech-section">
        <h2>Built with Modern Technologies</h2>
        <p>Powered by cutting-edge AI and robust infrastructure for optimal performance and reliability.</p>
        <div class="about-tech-tags">
            <span class="about-tech-tag">Google Gemini 1.5 Pro</span>
            <span class="about-tech-tag">Streamlit Framework</span>
            <span class="about-tech-tag">SQLite3 Database</span>
            <span class="about-tech-tag">Email OTP Security</span>
            <span class="about-tech-tag">PIL Image Processing</span>
            <span class="about-tech-tag">Cloud Integration</span>
            <span class="about-tech-tag">Advanced OCR</span>
            <span class="about-tech-tag">Real-time Processing</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Statistics Section
    st.title("📊 CodeGPT Statistics")
    st.markdown("""
    <div class="about-stats-grid">
        <div class="about-stat-card">
            <span class="about-stat-number">50+</span>
            <span class="about-stat-label">Languages Supported</span>
        </div>
        <div class="about-stat-card">
            <span class="about-stat-number">99.9%</span>
            <span class="about-stat-label">Accuracy Rate</span>
        </div>
        <div class="about-stat-card">
            <span class="about-stat-number">24/7</span>
            <span class="about-stat-label">Availability</span>
        </div>
        <div class="about-stat-card">
            <span class="about-stat-number">∞</span>
            <span class="about-stat-label">Learning Capacity</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Call to Action Section
    st.markdown("""
    <div class="about-cta-banner">
        <h2>Ready to Transform Your Coding Experience?</h2>
        <p>Join thousands of developers who are already using CodeGPT to write better, faster, and more efficient code every day. Start your journey to becoming a more productive developer today.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Close main wrapper
# AI functions
def query_gemini(prompt):
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    return response.text

def reply(input_text, image, prompt):
    model1 = genai.GenerativeModel("gemini-1.5-flash")
    response = model1.generate_content([input_text, image, prompt])
    return response.text

def save_chat_history(user_id, code_input, features_used, ai_output):
    if user_id:
        conn = sqlite3.connect('codegpt_users.db')
        c = conn.cursor()
        c.execute("INSERT INTO chat_history (user_id, code_input, features_used, ai_output) VALUES (?, ?, ?, ?)",
                 (user_id, code_input, ','.join(features_used), ai_output))
        conn.commit()
        conn.close()



from PIL import Image

def process_code(code_input, features_selected, uploaded_file=None):
    results = []
    
    if not features_selected:
        # Default analysis
        prompt = f"""
        Make the heading as *Finding & Fixing Bugs*
        Analyze the following code for errors and potential bugs. Identify syntax issues, logical errors, and performance inefficiencies. 
        Provide a list of errors with explanations and suggest fixes. Give headings in bold text. If there are no errors, mention that there are no errors.
        Code: {code_input}
        
        Make the heading as *Explanation of Code*
        Explain the following code in simple terms. Break it down step by step, describing what each function, loop, and condition does.
        
        Make the heading as *Optimizing Code*
        Optimize the following code to improve time and space efficiency.
        
        Make the heading as *Detect & Adapt Language*
        Detect the programming language and provide equivalent implementations in other languages.
        
        Make the heading as *Refactoring the Code*
        Refactor the following code to enhance readability, maintainability, and structure.
        """
        output = query_gemini(prompt)
        results.append(("Complete Analysis", output))
    else:
        for feature in features_selected:
            if feature == "📸 Convert Handwritten Code" and uploaded_file:
                image1 = Image.open(uploaded_file)
                st.image(image1, caption="Uploaded Image", use_column_width=True)
                prompt = "Analyze this handwritten code image and convert it to digital code. Provide explanation and fix any errors."
                output = reply("", image1, prompt)
                results.append((feature, output))
            
            elif feature == "🐛 Find & Fix Bugs":
                prompt = f"""*Finding & Fixing Bugs*
                
                Analyze the following code for errors and potential bugs. Identify syntax issues, logical errors, and performance inefficiencies.
                Code: {code_input}
                
                Output Format:
                - *Issue:* Describe the problem
                - *Errors Found:* List of errors with explanations
                - *Suggested Fix:* Provide corrected code
                - *Explanation:* Explain why the fix works
                """
                output = query_gemini(prompt)
                results.append((feature, output))
            
            elif feature == "📚 Explain Code":
                prompt = f"""*Code Explanation*
                
                Explain the following code in simple terms:
                {code_input}
                
                Output Format:
                - *Overview:* What the code does
                - *Step-by-Step Breakdown:* Explain each important line
                - *Key Concepts Used:* List algorithms, data structures, and logic patterns
                """
                output = query_gemini(prompt)
                results.append((feature, output))
            
            elif feature == "⚡ Optimize Code":
                prompt = f"""*Code Optimization*
                
                Optimize the following code:
                {code_input}
                
                Output Format:
                - *Current Issues:* Describe inefficiencies
                - *Optimized Code:*
                - *Explanation of Improvements:*
                - *Performance Impact:*
                """
                output = query_gemini(prompt)
                results.append((feature, output))
            
            elif feature == "🌍 Detect & Adapt Language":
                prompt = f"""*Language Detection & Adaptation*
                
                Detect the programming language and provide equivalent implementations java,c,c++,c#,java script,python,go,rust,typescript,php,swift,kotlin:
                {code_input}
                
                Output Format:
                - *Detected Language:*
                - *Equivalent Implementations in Other Languages:*
                """
                output = query_gemini(prompt)
                results.append((feature, output))
            
            elif feature == "🔄 Refactor Code":
                prompt = f"""*Code Refactoring*
                
                Refactor the following code:
                {code_input}
                
                Output Format:
                - *Refactored Code:*
                - *Key Improvements:*
                - *Enhanced Readability Features:*
                """
                output = query_gemini(prompt)
                results.append((feature, output))
    
    st.markdown("## -- Output -- ")
    # Display results
    for feature, output in results:
        st.markdown(f"### {feature}")
        with st.container():
            st.markdown(output)
            st.markdown("---")
    
    # Save to history if user is logged in
    if st.session_state.authenticated and results:
        combined_output = "\n\n".join([f"{feature}:\n{output}" for feature, output in results])
        save_chat_history(st.session_state.user_id, code_input, 
                         [f[0] for f in results], combined_output)
        st.success("💾 Analysis saved to your history!")

            



    if st.session_state.authenticated and results:
        combined_output = "\n\n".join([f"{feature}:\n{output}" for feature, output in results])
        save_chat_history(
            st.session_state.user_id,
            code_input,
            [f[0] for f in results],
            combined_output
        )




# Main application
def main_page():
    # Round logo + header
    st.markdown("""
        <div class="header">
            <h1>✨ CodeGPT ✨</h1>
            <p>🚀 Empower Your Coding with AI | Debug • Explain • Optimize</p>
        </div>
    """, unsafe_allow_html=True)

    # Greeting
    if st.session_state.authenticated:
        st.markdown(f"""
            <h3 style="text-align: center">Welcome back, {st.session_state.username}! 👋</h3>
            <p style="text-align: center">Your code analysis history is being saved automatically.</p>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <h3 style="text-align: center">Welcome to CodeGPT! 🎉</h3>
            <p style="text-align: center">You're using CodeGPT as a guest. Login to save your analysis history.</p>
        """, unsafe_allow_html=True)

    # Code Input Section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">📝 Code Input</div>', unsafe_allow_html=True)
    code_input = st.text_area("Paste your code here:", height=300, placeholder="Enter your code here...", key="code_input_1")
    st.markdown('</div>', unsafe_allow_html=True)

    # Feature Selection
    st.markdown("## 🎯 Choose Features")
    col1, col2, col3 = st.columns(3)
    with col1:
        find_bugs = st.checkbox("🐛 **Find & Fix Bugs**")
        explain_code = st.checkbox("📚 Explain Code")
    with col2:
        optimize_code = st.checkbox("⚡ Optimize Code")
        detect_language = st.checkbox("🌍 Detect & Adapt Language")
    with col3:
        refactor_code = st.checkbox("🔄 Refactor Code")
        convert_handwritten = st.checkbox("📸 Convert Handwritten")

    features_selected = []
    if find_bugs: features_selected.append("🐛 Find & Fix Bugs")
    if explain_code: features_selected.append("📚 Explain Code")
    if optimize_code: features_selected.append("⚡ Optimize Code")
    if detect_language: features_selected.append("🌍 Detect & Adapt Language")
    if refactor_code: features_selected.append("🔄 Refactor Code")

    uploaded_file = None
    if convert_handwritten:
        features_selected.append("📸 Convert Handwritten")
        uploaded_file = st.file_uploader("📸 Upload Handwritten Code Image", type=["png", "jpg", "jpeg"])

    # Action Buttons
    st.markdown("### 🎛 Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        analyze_all = st.button("🚀 Analyze All Features", type="primary")
    with col2:
        process_selected = st.button("✨ Process Selected Features")
    with col3:
        clear_all = st.button("🧹 Clear All")

    # Button Actions - now outside columns
    if analyze_all:
        if code_input or uploaded_file:
            with st.spinner("🤖 CodeGPT is analyzing your code..."):
                all_features = ["🐛 Find & Fix Bugs", "📚 Explain Code", "⚡ Optimize Code",
                                "🌍 Detect & Adapt Language", "🔄 Refactor Code"]
                process_code(code_input, all_features, uploaded_file)
        else:
            st.warning("Please provide code input or upload an image!")

    if process_selected:
        if features_selected and (code_input or uploaded_file):
            with st.spinner("🤖 COdeGPT is processing..."):
                process_code(code_input, features_selected, uploaded_file)
        elif not features_selected:
            st.warning("Please select at least one feature!")
        else:
            st.warning("Please provide code input or upload an image!")

    if clear_all:
        st.rerun()


def main():
    show_navigation()
    
    # Route to different pages based on current_page
    if st.session_state.current_page == 'main':
        main_page()
    elif st.session_state.current_page == 'login':
        login_page()
    elif st.session_state.current_page == 'signup':
        signup_page()
    elif st.session_state.current_page == 'verify_otp':
        verify_otp_page()
    elif st.session_state.current_page == 'profile':
        profile_page()
    elif st.session_state.current_page == 'history':
        history_page()
    elif st.session_state.current_page == 'about':
        about_page()
    elif st.session_state.current_page == 'contact':
        contactus()


# Footer
def show_footer():
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px; color: #666;'>
        <h4>🚀 TEAM ARJUNA — Innovating at the Speed of Thought</h4>
        <p>🧠 Powered by <strong>Google Gemini AI</strong> | 🔧 Built with <strong>Streamlit</strong></p>
        <p style='font-size: 0.8em; margin-top: 15px;'>© 2025 CodeGPT. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)



# Run the application
if __name__ == "__main__":
    main()
    show_footer()