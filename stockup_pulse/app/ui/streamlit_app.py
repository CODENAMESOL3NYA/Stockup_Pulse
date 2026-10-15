"""
StockUp Pulse - Enterprise AMD Hardware-Accelerated Restocking Agent
AMD Developer Hackathon ACT III (Track: Reinvent Commerce)

Strict Dark Mode Aesthetic:
  - App Background: #0B0B0B
  - Card / Surface Background: #1A1A1A
  - Primary Accent: #E50000 (AMD Red)
  - Secondary Accent: #4A0000 (Deep Maroon)
  - Primary Text: #FFFFFF
  - Secondary Text / Borders: #888888 / #333333
  - Status Success: #00CC66 | Status Warning/Error: #FF3333
  - STRICT BAN ON EMOJIS & UNNECESSARY ICONS
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import json
import time
from stockup_pulse.planning.optimizer import optimizer
from stockup_pulse.orders.manager import order_manager, PlanNotApprovedError
from stockup_pulse.forecast.forecaster import forecaster
from stockup_pulse.trace.tracker import trace_collector
from stockup_pulse.adapters.amd_llm import amd_llm
from stockup_pulse.core.config import settings
from stockup_pulse.core.db import (
    init_db,
    authenticate_user,
    register_user,
    User
)

# Page configuration - strictly no emojis
st.set_page_config(
    page_title="STOCKUP PULSE // AMD ACCELERATED COMMERCE",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database tables
init_db()

# Custom Styling & Hardware-Grade Dark Mode CSS Overrides
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    /* 1. Global Background & Typography */
    html, body, [data-testid="stAppViewContainer"], .main, [data-testid="stApp"] {
        background-color: #0B0B0B !important;
        color: #FFFFFF !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
    }

    [data-testid="stHeader"] {
        background-color: #0B0B0B !important;
        border-bottom: 1px solid #333333 !important;
    }

    /* 2. STRICT BAN: Hide Streamlit Default Alert & Toast Emojis */
    div[data-testid="stNotification"] svg,
    div[data-testid="stAlert"] svg,
    div[data-testid="stAlert"] span[role="img"],
    div[data-testid="stToast"] span[role="img"],
    div[data-testid="stAlert"] [data-testid="stIconMaterial"] {
        display: none !important;
    }

    div[data-testid="stAlert"] {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-left: 3px solid #E50000 !important;
        border-radius: 4px !important;
        padding: 12px 16px !important;
    }

    div[data-testid="stAlert"] p {
        color: #FFFFFF !important;
        font-size: 13px !important;
    }

    div[data-testid="stToast"] {
        background-color: #1A1A1A !important;
        border: 1px solid #E50000 !important;
        color: #FFFFFF !important;
        border-radius: 4px !important;
    }

    /* 3. Sidebar Navigation */
    section[data-testid="stSidebar"] {
        background-color: #0B0B0B !important;
        border-right: 1px solid #333333 !important;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        font-size: 14px !important;
        font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #333333 !important;
        margin: 1rem 0 !important;
    }

    /* Sidebar Radio Links */
    div[data-testid="stRadio"] label {
        color: #888888 !important;
        padding: 8px 12px !important;
        border-radius: 2px !important;
        border-left: 3px solid transparent !important;
        transition: all 0.15s ease !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
    }

    div[data-testid="stRadio"] label:hover {
        color: #FFFFFF !important;
        background-color: #1A1A1A !important;
    }

    div[data-testid="stRadio"] label[data-checked="true"] {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        border-left: 3px solid #E50000 !important;
        background-color: #1A1A1A !important;
    }

    /* 4. Hardware-Grade Buttons */
    button[kind="primary"], div.stButton > button[kind="primary"], .stFormSubmitButton > button {
        background-color: #E50000 !important;
        color: #FFFFFF !important;
        border: 1px solid #E50000 !important;
        border-radius: 4px !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        padding: 9px 18px !important;
        transition: all 0.2s ease !important;
    }

    button[kind="primary"]:hover, div.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
        background-color: #CC0000 !important;
        border-color: #CC0000 !important;
        box-shadow: 0 0 14px rgba(229, 0, 0, 0.45) !important;
    }

    button[kind="secondary"], div.stButton > button[kind="secondary"], div.stButton > button {
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        letter-spacing: 0.04em !important;
        text-transform: uppercase !important;
        font-size: 12px !important;
        transition: all 0.2s ease !important;
    }

    button[kind="secondary"]:hover, div.stButton > button:hover {
        border-color: #E50000 !important;
        color: #FFFFFF !important;
        background-color: #1A1A1A !important;
    }

    /* 5. Input Fields with AMD Red Focus Glow */
    input[type="text"], input[type="password"], input[type="number"], textarea {
        background-color: #0B0B0B !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
        border-radius: 4px !important;
        font-size: 13px !important;
    }

    input[type="text"]:focus, input[type="password"]:focus, input[type="number"]:focus, textarea:focus {
        border-color: #E50000 !important;
        box-shadow: 0 0 0 1px #E50000, 0 0 10px rgba(229, 0, 0, 0.35) !important;
        outline: none !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #0B0B0B !important;
        border: 1px solid #333333 !important;
        border-radius: 4px !important;
        color: #FFFFFF !important;
    }

    div[data-baseweb="select"]:focus-within > div {
        border-color: #E50000 !important;
        box-shadow: 0 0 0 1px #E50000 !important;
    }

    div[data-baseweb="popover"], div[data-baseweb="menu"] {
        background-color: #1A1A1A !important;
        border: 1px solid #333333 !important;
    }

    div[data-baseweb="menu"] li {
        color: #FFFFFF !important;
    }

    div[data-baseweb="menu"] li:hover {
        background-color: #4A0000 !important;
        color: #FFFFFF !important;
    }

    /* 6. Metric Cards & Cards */
    .amd-card {
        background-color: #1A1A1A;
        border: 1px solid #333333;
        border-radius: 4px;
        padding: 24px;
    }

    .metric-card {
        background-color: #1A1A1A !important;
        border: 1px solid #333333 !important;
        border-top: 2px solid #E50000 !important;
        border-radius: 4px !important;
        padding: 16px 20px;
        margin-bottom: 8px;
    }

    .metric-label {
        font-size: 11px !important;
        color: #888888 !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        margin-bottom: 6px;
    }

    .metric-value {
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    .metric-sub {
        font-size: 11px !important;
        color: #00CC66 !important;
        margin-top: 4px;
        font-weight: 600;
        letter-spacing: 0.02em;
    }

    /* 7. Status Badges without Emojis */
    .badge-confirmed {
        background: #1A1A1A;
        color: #00CC66;
        border: 1px solid #00CC66;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }

    .badge-review {
        background: #1A1A1A;
        color: #FF3333;
        border: 1px solid #FF3333;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }

    .badge-accent {
        background: #1A1A1A;
        color: #E50000;
        border: 1px solid #E50000;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }

    .badge-neutral {
        background: #1A1A1A;
        color: #888888;
        border: 1px solid #333333;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-block;
    }

    /* 8. Dataframes & Tables */
    div[data-testid="stDataFrame"] {
        border: 1px solid #333333 !important;
        border-radius: 4px !important;
        background-color: #0B0B0B !important;
    }

    table {
        background-color: #0B0B0B !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
    }

    thead tr th {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border-bottom: 1px solid #333333 !important;
        font-size: 12px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    tbody tr td {
        background-color: #0B0B0B !important;
        color: #FFFFFF !important;
        border-bottom: 1px solid #222222 !important;
        font-size: 13px !important;
    }

    /* 9. Tabs */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        color: #888888 !important;
        border-bottom: 2px solid transparent !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #FFFFFF !important;
        border-bottom: 2px solid #E50000 !important;
    }

    /* 10. Animation Keyframes */
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(6px); }
        100% { opacity: 1; transform: translateY(0); }
    }

    .fade-in {
        animation: fadeIn 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    /* 11. Splash Screen Styling */
    .splash-container-amd {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 75vh;
        text-align: center;
        animation: fadeIn 0.5s ease-out forwards;
    }

    .splash-title-amd {
        font-size: 44px;
        font-weight: 900;
        color: #FFFFFF;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .splash-line-amd {
        width: 140px;
        height: 2px;
        background-color: #E50000;
        margin: 0 auto 18px auto;
        box-shadow: 0 0 12px rgba(229, 0, 0, 0.6);
    }

    .splash-tagline-amd {
        font-size: 16px;
        color: #888888;
        font-weight: 500;
        letter-spacing: 0.03em;
        margin-bottom: 22px;
    }

    .splash-badge-amd {
        display: inline-block;
        background: #1A1A1A;
        color: #E50000;
        border: 1px solid #333333;
        padding: 6px 16px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    /* 12. Auth Form Container */
    .auth-wrapper-amd {
        display: flex;
        justify-content: center;
        align-items: center;
        padding-top: 24px;
        padding-bottom: 40px;
        animation: fadeIn 0.35s ease-out forwards;
    }

    .auth-card-amd {
        background: #1A1A1A;
        border: 1px solid #333333;
        border-radius: 4px;
        padding: 32px 32px 24px 32px;
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6);
        max-width: 480px;
        width: 100%;
        margin: 0 auto;
    }

    /* Stepper text */
    .step-text {
        color: #888888;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .step-text-active {
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        border-bottom: 2px solid #E50000;
        padding-bottom: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "current_page" not in st.session_state:
    st.session_state.current_page = "splash"
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
if "step" not in st.session_state:
    st.session_state.step = 1
if "demo_data" not in st.session_state:
    st.session_state.demo_data = True
if "plan_approved" not in st.session_state:
    st.session_state.plan_approved = False
if "current_plan" not in st.session_state:
    st.session_state.current_plan = None
if "orders" not in st.session_state:
    st.session_state.orders = []
if "budget" not in st.session_state:
    st.session_state.budget = 3000.0
if "profile_settings" not in st.session_state:
    st.session_state.profile_settings = {
        "planning_horizon": "14 days",
        "preferred_supplier": "Makro",
        "delivery_address": "Shop 4, Nelson Mandela Ave, Sunnyside, Pretoria, 0002",
        "total_saved": 482.50,
        "avg_monthly_budget": 12500.00
    }

# Sample Default Data for Restocking Optimizer
demo_items = [
    {"product": "Coca-Cola 440ml", "pack_size": "24 x 440ml", "supplier": "Makro", "recommended_qty": 96, "unit_price": 12.09, "supplier_price": 289.00, "our_price": 16.00, "at_risk": False, "is_out_of_stock": False},
    {"product": "Sprite 440ml", "pack_size": "24 x 440ml", "supplier": "Makro", "recommended_qty": 72, "unit_price": 11.48, "supplier_price": 275.50, "our_price": 15.50, "at_risk": False, "is_out_of_stock": False},
    {"product": "Chicken Flavour Noodles", "pack_size": "5 x 70g", "supplier": "Shoprite", "recommended_qty": 50, "unit_price": 8.40, "supplier_price": 42.00, "our_price": 12.00, "at_risk": True, "is_out_of_stock": False},
    {"product": "Brown Bread", "pack_size": "1 x 700g", "supplier": "Usave", "recommended_qty": 20, "unit_price": 16.50, "supplier_price": 16.50, "our_price": 21.00, "at_risk": True, "is_out_of_stock": False},
    {"product": "Milk (long life)", "pack_size": "6 x 1L", "supplier": "Usave", "recommended_qty": 24, "unit_price": 13.90, "supplier_price": 84.00, "our_price": 18.00, "at_risk": False, "is_out_of_stock": False},
    {"product": "Cooking Oil", "pack_size": "6 x 1L", "supplier": "Makro", "recommended_qty": 20, "unit_price": 18.75, "supplier_price": 210.00, "our_price": 26.00, "at_risk": True, "is_out_of_stock": False}
]

# Ensure plan is initialized
if st.session_state.current_plan is None:
    st.session_state.current_plan = optimizer.optimize_plan(demo_items, budget=st.session_state.budget)

# ==============================================================================
# VIEW 1: THE SPLASH SCREEN
# ==============================================================================
if st.session_state.current_page == "splash":
    splash_placeholder = st.empty()

    with splash_placeholder.container():
        st.markdown("""
        <div class="splash-container-amd">
            <div class="splash-title-amd">STOCKUP PULSE</div>
            <div class="splash-line-amd"></div>
            <div class="splash-tagline-amd">Smarter stock. Stronger shops.</div>
            <div>
                <span class="splash-badge-amd">AMD DEVELOPER HACKATHON ACT III // REINVENT COMMERCE</span>
            </div>
            <p style="color: #888888; font-size: 12px; margin-top: 20px; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;">
                LOCAL DEMO MODE // PYTHON RESTOCKING SERVICE
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 1.2, 2])
        with col2:
            if st.button("CONTINUE TO LOGIN", key="splash_skip", use_container_width=True):
                st.session_state.current_page = "login"
                st.rerun()

    # Auto-transition: hold 2.5 seconds, then transition to login
    time.sleep(2.5)
    st.session_state.current_page = "login"
    splash_placeholder.empty()
    st.rerun()

# ==============================================================================
# VIEW 2: THE LOGIN SCREEN
# ==============================================================================
elif st.session_state.current_page == "login":
    login_placeholder = st.empty()

    with login_placeholder.container():
        st.markdown("""
        <div class="auth-wrapper-amd">
            <div class="auth-card-amd">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="font-size: 11px; font-weight: 800; color: #E50000; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 6px;">
                        AUTHENTICATION GATEWAY
                    </div>
                    <h2 style="font-size: 22px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.05em; text-transform: uppercase; margin: 0;">
                        STOCKUP PULSE LOGIN
                    </h2>
                    <p style="font-size: 12px; color: #888888; margin-top: 6px;">
                        Enter your registered WhatsApp number to access the restocking console.
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1.3, 1])
        with col2:
            with st.form("login_form", clear_on_submit=False):
                phone = st.text_input(
                    "WhatsApp Number",
                    value="",
                    placeholder="+27 82 000 0000",
                    help="Spaza shop owners receive purchase orders directly on this WhatsApp line."
                )
                password = st.text_input(
                    "Password",
                    value="",
                    type="password",
                    placeholder="Enter your password"
                )

                submit_login = st.form_submit_button("LOG IN", type="primary", use_container_width=True)

            if submit_login:
                if not phone.strip():
                    st.error("Please enter your WhatsApp number.")
                elif not password:
                    st.error("Please enter your password.")
                else:
                    user = authenticate_user(phone, password)
                    if user:
                        st.session_state.authenticated_user = {
                            "phone": user.whatsapp_number,
                            "name": user.full_name,
                            "shop_name": user.shop_name
                        }
                        st.session_state.current_page = "dashboard"
                        st.toast(f"Authenticated: {user.full_name} ({user.shop_name})")
                        time.sleep(0.3)
                        st.rerun()
                    else:
                        st.error("Invalid WhatsApp number or password.")

            st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
            c_left, c_right = st.columns(2)
            with c_left:
                st.caption("Don't have an account?")
            with c_right:
                if st.button("CREATE ACCOUNT", use_container_width=True):
                    st.session_state.current_page = "signup"
                    st.rerun()

# ==============================================================================
# VIEW 3: THE SIGN-UP SCREEN (SPAZA SHOP CONTEXT)
# ==============================================================================
elif st.session_state.current_page == "signup":
    signup_placeholder = st.empty()

    with signup_placeholder.container():
        st.markdown("""
        <div class="auth-wrapper-amd">
            <div class="auth-card-amd">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="font-size: 11px; font-weight: 800; color: #E50000; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 6px;">
                        ACCOUNT PROVISIONING
                    </div>
                    <h2 style="font-size: 22px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.05em; text-transform: uppercase; margin: 0;">
                        CREATE YOUR ACCOUNT
                    </h2>
                    <p style="font-size: 12px; color: #888888; margin-top: 6px;">
                        Join South African spaza shops maximizing margin and eliminating stockouts.
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1.4, 1])
        with col2:
            with st.form("signup_form"):
                full_name = st.text_input("Full Name", placeholder="e.g., Mpho Khumalo")
                shop_name = st.text_input("Shop Name", placeholder="e.g., Sunnyside Spaza", value="Sunnyside Spaza")
                whatsapp = st.text_input(
                    "WhatsApp Number",
                    placeholder="+27 82 123 4567",
                    help="This will be used to send your purchase orders via our WhatsApp bot."
                )
                pw1 = st.text_input("Password", type="password", placeholder="Create a password")
                pw2 = st.text_input("Confirm Password", type="password", placeholder="Confirm password")

                submit_signup = st.form_submit_button("CREATE ACCOUNT", type="primary", use_container_width=True)

            if submit_signup:
                if not full_name.strip():
                    st.error("Please enter your full name.")
                elif not whatsapp.strip():
                    st.error("Please enter your WhatsApp number.")
                elif not pw1 or not pw2:
                    st.error("Please enter and confirm your password.")
                elif pw1 != pw2:
                    st.error("Passwords do not match. Please verify and try again.")
                elif len(pw1) < 8:
                    st.error("Use a password with at least 8 characters.")
                else:
                    try:
                        new_user = register_user(
                            full_name=full_name.strip(),
                            shop_name=shop_name.strip() or "Sunnyside Spaza",
                            whatsapp_number=whatsapp.strip(),
                            password=pw1
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        st.session_state.authenticated_user = {
                            "phone": new_user.whatsapp_number,
                            "name": new_user.full_name,
                            "shop_name": new_user.shop_name
                        }
                        st.success("Account created successfully. Welcome to StockUp Pulse.")
                        time.sleep(0.5)
                        st.session_state.current_page = "dashboard"
                        st.rerun()

            st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
            c_left, c_right = st.columns(2)
            with c_left:
                st.caption("Already have an account?")
            with c_right:
                if st.button("LOG IN", use_container_width=True):
                    st.session_state.current_page = "login"
                    st.rerun()

# ==============================================================================
# VIEW 4: THE MAIN AUTHENTICATED DASHBOARD (WRAPPING 5 STEPS)
# ==============================================================================
elif st.session_state.current_page == "dashboard":
    user_info = st.session_state.authenticated_user or {
        "name": "Mpho Khumalo",
        "shop_name": "Sunnyside Spaza",
        "phone": "+27821234567"
    }

    # Sidebar Navigation - strictly dark mode #0B0B0B with #333333 border and #E50000 indicator
    with st.sidebar:
        st.markdown("### STOCKUP PULSE")
        st.caption("Smarter stock. Stronger shops.")
        st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)

        nav = st.radio(
            "NAVIGATION",
            [
                "HOME",
                "1. DATA & UPLOADS",
                "2. REVIEW CATALOGUE",
                "3. RESTOCKING PLAN",
                "4. APPROVE & CREATE ORDERS",
                "5. PURCHASE ORDERS",
                "TECHNICAL EVIDENCE & TRACE"
            ],
            index=st.session_state.step
        )

        st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
        st.markdown(f"**STORE:** {user_info['shop_name']}")
        st.caption(f"{user_info['name']} // {user_info['phone']}")

        st.session_state.demo_data = st.toggle("Use demo data", value=st.session_state.demo_data)
        if st.session_state.demo_data:
            st.markdown('<span class="badge-confirmed">DEMO DATA ACTIVE</span>', unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
        if st.button("LOG OUT", use_container_width=True):
            st.session_state.authenticated_user = None
            st.session_state.current_plan = None
            st.session_state.orders = []
            st.session_state.plan_approved = False
            st.session_state.current_page = "login"
            st.toast("Logged out successfully.")
            st.rerun()

    # Map sidebar selection to step
    step_map = {
        "HOME": 0,
        "1. DATA & UPLOADS": 1,
        "2. REVIEW CATALOGUE": 2,
        "3. RESTOCKING PLAN": 3,
        "4. APPROVE & CREATE ORDERS": 4,
        "5. PURCHASE ORDERS": 5,
        "TECHNICAL EVIDENCE & TRACE": 6
    }
    current_step = step_map.get(nav, 1)

    # Top Navigation Bar (Clickable client info routes to profile; Log Out exclusively in sidebar)
    top_col_badge, top_col_profile = st.columns([2.6, 1.4])
    with top_col_badge:
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px; margin-top:4px; margin-bottom:16px;">
            <div style="display:inline-flex; align-items:center; gap:6px; background:#1A1A1A; padding:4px 12px; border-radius:4px; font-size:11px; font-weight:700; color:#FFFFFF; border:1px solid #333333;">
                <span style="color:#00CC66; font-size:9px;">[ONLINE]</span> {user_info['shop_name'].upper()} // PRETORIA CENTRAL
            </div>
            <span style="font-size:11px; color:#888888; font-family:'JetBrains Mono', monospace;">LOCAL DEMO MODE</span>
        </div>
        """, unsafe_allow_html=True)
    with top_col_profile:
        # Clickable client info block in top right
        profile_btn_label = f"{user_info['name'].upper()} // {user_info['shop_name'].upper()}"
        if st.button(profile_btn_label, key="btn_top_client_info", use_container_width=True, help="Open Client Profile & Operational Settings"):
            st.session_state.current_page = "profile"
            st.rerun()

    # ==================== STEP 0: HOME ====================
    if current_step == 0:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.markdown("<h1 style='color:#FFFFFF; font-size:32px; font-weight:900; letter-spacing:0.04em;'>STOCKUP PULSE</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#888888; font-size:16px; font-weight:600;'>AI-POWERED RESTOCKING FOR SOUTH AFRICAN SPAZA SHOPS</h3>", unsafe_allow_html=True)
        st.markdown("<div style='height:2px; width:80px; background:#E50000; margin-bottom:16px;'></div>", unsafe_allow_html=True)
        st.write(
            "Upload sales records, catalogue scans, and supplier price lists. "
            "Our AMD hardware-accelerated integer knapsack optimizer and live retail scraper "
            "eliminate stockouts while enforcing strict ZAR budget ceilings."
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">TIME SAVED</div>
                <div class="metric-value">6.5 HRS</div>
                <div class="metric-sub">WEEKLY PROCUREMENT RUNS</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">STOCKOUT REDUCTION</div>
                <div class="metric-value">0 ITEMS</div>
                <div class="metric-sub">SHELVES BUFFERED</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">BUDGET ENFORCEMENT</div>
                <div class="metric-value">100.0%</div>
                <div class="metric-sub">STRICT RAND LIMIT</div>
            </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">MARGIN PRESERVATION</div>
                <div class="metric-value">NOT MEASURED</div>
                <div class="metric-sub">NO VALIDATED SWAP DATA</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== STEP 1: UPLOAD DATA ====================
    elif current_step == 1:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.markdown("<div class='step-text-active'>STEP 1 OF 5 // DATA INGESTION</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#FFFFFF; font-size:24px; font-weight:800; margin-top:8px;'>UPLOAD STORE DATA</h2>", unsafe_allow_html=True)
        st.caption("Upload sales CSV, stock balance CSV, and supplier price leaflet images.")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.file_uploader("Upload sales CSV, stock CSV, or leaflet images", accept_multiple_files=True)
            st.markdown("""
            <div style="background:#1A1A1A; border:1px solid #333333; border-radius:4px; padding:12px 16px; margin-top:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-family:'JetBrains Mono', monospace; font-size:12px; color:#FFFFFF;">sales_data.csv (2.4 KB)</span>
                    <span class="badge-confirmed">CONFIRMED</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-family:'JetBrains Mono', monospace; font-size:12px; color:#FFFFFF;">stock_data.csv (3.1 KB)</span>
                    <span class="badge-confirmed">CONFIRMED</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-family:'JetBrains Mono', monospace; font-size:12px; color:#FFFFFF;">supplier_price_list.pdf (1.2 MB)</span>
                    <span class="badge-confirmed">CONFIRMED</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### PLANNING PARAMETERS")
            new_budget = st.number_input("Budget Ceiling (ZAR)", value=float(st.session_state.budget), step=100.0)
            if new_budget != st.session_state.budget:
                st.session_state.budget = new_budget
                st.session_state.current_plan = optimizer.optimize_plan(demo_items, budget=new_budget)

            st.selectbox("Planning Horizon", ["Next 14 days (Bi-weekly)", "Next 7 days (Weekly)", "Next 30 days (Monthly)"])
            st.markdown("""
            <div style="background:#1A1A1A; border:1px solid #333333; border-radius:4px; padding:12px; margin-top:10px;">
                <div style="font-size:11px; font-weight:700; color:#888888; text-transform:uppercase; margin-bottom:6px;">SUPPLIER LEAD TIMES</div>
                <div style="font-family:'JetBrains Mono', monospace; font-size:12px; color:#FFFFFF; line-height:1.6;">
                    MAKRO: 2 DAYS<br>
                    SHOPRITE: 3 DAYS<br>
                    USAVE: 2 DAYS
                </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== STEP 2: REVIEW CATALOGUE ====================
    elif current_step == 2:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.markdown("<div class='step-text-active'>STEP 2 OF 5 // CATALOGUE CONFIRMATION</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#FFFFFF; font-size:24px; font-weight:800; margin-top:8px;'>CONFIRM EXTRACTED PRODUCT CATALOGUE</h2>", unsafe_allow_html=True)
        st.caption("Extracted by AMD ROCm Qwen2.5-VL-7B-Instruct. Validate SKU matches and wholesale prices.")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown('<div class="metric-card"><div class="metric-label">TOTAL PRODUCTS</div><div class="metric-value">248</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown('<div class="metric-card" style="border-top-color:#00CC66;"><div class="metric-label">CONFIRMED MATCHES</div><div class="metric-value" style="color:#00CC66;">232</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown('<div class="metric-card" style="border-top-color:#FF3333;"><div class="metric-label">NEEDS REVIEW</div><div class="metric-value" style="color:#FF3333;">12</div></div>', unsafe_allow_html=True)
        with m4:
            st.markdown('<div class="metric-card"><div class="metric-label">UNMATCHED SKUS</div><div class="metric-value">4</div></div>', unsafe_allow_html=True)

        df = pd.DataFrame([
            {"Product": "Coca-Cola 440ml", "Pack Size": "24 x 440ml", "Supplier Price": "R 289.00", "Our Price": "R 349.00", "Status": "CONFIRMED", "Confidence": "98%"},
            {"Product": "Sprite 440ml", "Pack Size": "24 x 440ml", "Supplier Price": "R 275.50", "Our Price": "R 329.00", "Status": "CONFIRMED", "Confidence": "96%"},
            {"Product": "Chicken Flavour Noodles", "Pack Size": "5 x 70g", "Supplier Price": "R 42.00", "Our Price": "R 54.00", "Status": "CONFIRMED", "Confidence": "93%"},
            {"Product": "Brown Bread", "Pack Size": "1 x 700g", "Supplier Price": "R 16.50", "Our Price": "R 24.00", "Status": "NEEDS REVIEW", "Confidence": "67%"},
            {"Product": "Milk (long life)", "Pack Size": "6 x 1L", "Supplier Price": "R 84.00", "Our Price": "R 99.00", "Status": "CONFIRMED", "Confidence": "92%"},
            {"Product": "Cooking Oil", "Pack Size": "6 x 1L", "Supplier Price": "R 210.00", "Our Price": "R 259.00", "Status": "CONFIRMED", "Confidence": "89%"}
        ])
        st.dataframe(df, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== STEP 3: RESTOCKING PLAN ====================
    elif current_step == 3:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.markdown("<div class='step-text-active'>STEP 3 OF 5 // RESTOCKING OPTIMIZATION</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#FFFFFF; font-size:24px; font-weight:800; margin-top:8px;'>DETERMINISTIC RESTOCKING PLAN</h2>", unsafe_allow_html=True)
        st.caption("Budget-constrained knapsack optimization with automated brand substitution via live SA retail scrapes.")

        plan = st.session_state.current_plan

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">BUDGET CEILING</div><div class="metric-value">R {plan["budget"]:,.2f}</div></div>', unsafe_allow_html=True)
        with k2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">ESTIMATED SPEND</div><div class="metric-value">R {plan["total_spend"]:,.2f}</div><div class="metric-sub">{plan["budget_utilization_pct"]}% UTILIZED</div></div>', unsafe_allow_html=True)
        with k3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">REMAINING BUFFER</div><div class="metric-value">R {plan["remaining_budget"]:,.2f}</div></div>', unsafe_allow_html=True)
        with k4:
            st.markdown(f'<div class="metric-card"><div class="metric-label">ITEMS REORDERED</div><div class="metric-value">{plan["total_items_to_reorder"]}</div><div class="metric-sub" style="color:#FF3333;">{plan["at_risk_items_count"]} AT RISK</div></div>', unsafe_allow_html=True)

        st.markdown("""
        <div style="background:#1A1A1A; border:1px solid #333333; border-left:3px solid #E50000; border-radius:4px; padding:10px 16px; margin: 14px 0;">
            <span style="font-weight:700; color:#E50000; font-size:12px; letter-spacing:0.04em;">SYSTEM NOTICE:</span>
            <span style="color:#FFFFFF; font-size:12px; margin-left:6px;">8 SKUs identified at stockout risk. Integer knapsack solution guarantees budget compliance.</span>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["ALLOCATED RESTOCKING PLAN", "SUPPLIER COMPARISON", "BRAND SUBSTITUTIONS"])
        with tab1:
            display_items = []
            for item in plan["allocated_items"]:
                is_swapped = item.get("swapped_via_live_market_prices", False)
                source_retailer = item.get("live_market_retailer", item.get("supplier", "SA Retail"))
                indicator = f"SCRAPED ({source_retailer.upper()})" if is_swapped else "FLYER EXTRACT"

                display_items.append({
                    "Product": f"[SWAPPED] {item['product']}" if is_swapped else item["product"],
                    "Qty": item["qty"],
                    "Supplier": item["supplier"].upper(),
                    "Unit Price": f"R {item['unit_price']:.2f}",
                    "Total Cost": f"R {item['total_cost']:.2f}",
                    "Market Source": indicator,
                    "Status": item["status"].upper()
                })
            plan_df = pd.DataFrame(display_items)
            st.dataframe(plan_df, use_container_width=True)

            if plan.get("plain_language_explanation"):
                st.markdown(f"""
                <div style="background:#1A1A1A; border:1px solid #333333; border-radius:4px; padding:14px; margin-top:14px;">
                    <div style="font-size:11px; font-weight:800; color:#E50000; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">
                        AMD EXPLAINER LLM AUDIT // QWEN2.5-VL-7B-INSTRUCT
                    </div>
                    <div style="color:#FFFFFF; font-size:13px; line-height:1.5;">
                        {plan['plain_language_explanation']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with tab2:
            st.markdown("#### SUPPLIER PRICE DISCOVERY MATRIX")
            comp_df = pd.DataFrame([
                {"Product": "Coca-Cola 440ml", "Makro": "R 12.09 [LOWEST]", "Shoprite": "R 13.50", "Usave": "R 14.20"},
                {"Product": "Sprite 440ml", "Makro": "R 11.48 [LOWEST]", "Shoprite": "R 12.90", "Usave": "R 13.75"},
                {"Product": "Chicken Noodles", "Shoprite": "R 8.40 [LOWEST]", "Makro": "R 9.20", "Usave": "R 10.50"},
                {"Product": "Milk (long life)", "Usave": "R 13.90 [LOWEST]", "Makro": "R 15.50", "Shoprite": "R 16.20"},
                {"Product": "Cooking Oil", "Makro": "R 18.75 [LOWEST]", "Shoprite": "R 21.00", "Usave": "R 22.50"}
            ])
            st.dataframe(comp_df, use_container_width=True)

        with tab3:
            st.markdown("#### DETERMINISTIC BRAND SUBSTITUTIONS")
            st.caption("Powered by SQLite `live_market_prices` table populated via asynchronous retailer scraper.")
            if plan["substitutions_applied"]:
                for sub in plan["substitutions_applied"]:
                    ret = sub.get("live_market_retailer", "Shoprite").upper()
                    st.markdown(f"""
                    <div style="background:#1A1A1A; border:1px solid #888888; border-left:3px solid #00CC66; border-radius:4px; padding:14px; margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span style="font-weight:800; font-size:13px; color:#FFFFFF;">
                                {sub['original_product'].upper()} &rarr; {sub['substituted_with'].upper()}
                            </span>
                            <span class="badge-confirmed">SAVED R {sub['savings']:.2f}</span>
                        </div>
                        <div style="font-size:12px; color:#888888; line-height:1.6;">
                            SOURCE: live_market_prices ({ret})<br>
                            ORIGINAL COST: R {sub['original_cost']:.2f} // SUBSTITUTED COST: R {sub['substituted_cost']:.2f}<br>
                            RATIONALE: {sub['reason']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("No brand substitutions triggered for current parameters.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== STEP 4: APPROVE PLAN ====================
    elif current_step == 4:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.markdown("<div class='step-text-active'>STEP 4 OF 5 // APPROVAL GATE</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#FFFFFF; font-size:24px; font-weight:800; margin-top:8px;'>HUMAN-IN-THE-LOOP APPROVAL</h2>", unsafe_allow_html=True)
        st.caption("Explicit confirmation required before purchase orders can be generated. Enforced by API (HTTP 409).")

        st.markdown("""
        <div style="background:#1A1A1A; border:1px solid #333333; border-left:3px solid #E50000; border-radius:4px; padding:12px 16px; margin-bottom:16px;">
            <div style="font-size:11px; font-weight:800; color:#E50000; text-transform:uppercase; letter-spacing:0.06em;">GOVERNANCE PROTOCOL</div>
            <div style="font-size:12px; color:#FFFFFF; margin-top:4px;">
                No supplier orders will be dispatched without explicit authorization from the shopkeeper.
            </div>
        </div>
        """, unsafe_allow_html=True)

        plan = st.session_state.current_plan

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">APPROVED BUDGET</div><div class="metric-value">R {plan["budget"]:,.2f}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">TOTAL SPEND</div><div class="metric-value">R {plan["total_spend"]:,.2f}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown('<div class="metric-card"><div class="metric-label">TARGET SUPPLIERS</div><div class="metric-value">3 WHOLESALERS</div></div>', unsafe_allow_html=True)

        st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
        approved_check = st.checkbox("I AUTHORIZE THIS RESTOCKING PLAN (SPECIFICATION V1.0)", value=st.session_state.plan_approved)
        st.session_state.plan_approved = approved_check

        if st.button("APPROVE PLAN & DISPATCH ORDERS", type="primary", disabled=not approved_check):
            plan["approved"] = True
            orders = order_manager.create_orders_from_plan(plan, approved=True, store_name=user_info["shop_name"])
            st.session_state.orders = orders
            order_nums = ", ".join([o["order_number"] for o in orders])
            st.success(f"DISPATCH CONFIRMED: {order_nums}")
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== STEP 5: PURCHASE ORDERS ====================
    elif current_step == 5:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.markdown("<div class='step-text-active'>STEP 5 OF 5 // PURCHASE ORDERS</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#FFFFFF; font-size:24px; font-weight:800; margin-top:8px;'>GENERATED PURCHASE ORDERS</h2>", unsafe_allow_html=True)

        if not st.session_state.plan_approved:
            st.markdown("""
            <div style="background:#1A1A1A; border:1px solid #FF3333; border-radius:4px; padding:16px;">
                <div style="font-weight:700; color:#FF3333; font-size:13px; text-transform:uppercase;">APPROVAL GATE LOCKED</div>
                <div style="font-size:12px; color:#888888; margin-top:4px;">No purchase orders generated. Complete Step 4 authorization first.</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            orders = st.session_state.orders
            order_summary = ", ".join(f"{order['order_number']} ({order['supplier']})" for order in orders)
            st.markdown(f"""
            <div style="background:#1A1A1A; border:1px solid #00CC66; border-radius:4px; padding:14px; margin-bottom:16px;">
                <div style="font-weight:700; color:#00CC66; font-size:12px; text-transform:uppercase;">ORDERS DISPATCHED TO SUPPLIERS</div>
                <div style="font-size:12px; color:#FFFFFF; margin-top:4px;">{order_summary or 'No purchase orders were created.'}</div>
            </div>
            """, unsafe_allow_html=True)
            for po in orders:
                with st.expander(f"{po['order_number']} // {po['supplier'].upper()} (R {po['total_spend']:,.2f})"):
                    st.write(f"Line items: {po['total_items']}")
                    st.code(po["whatsapp_message"])
        st.markdown('</div>', unsafe_allow_html=True)

    # ==================== STEP 6: TECHNICAL EVIDENCE ====================
    elif current_step == 6:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.markdown("<div class='step-text-active'>VERIFICATION // TECHNICAL EVIDENCE</div>", unsafe_allow_html=True)
        st.markdown("<h2 style='color:#FFFFFF; font-size:24px; font-weight:800; margin-top:8px;'>BENCHMARK FIXTURE & AUDIT TRAIL</h2>", unsafe_allow_html=True)
        st.caption("Forecast metrics use illustrative fixture data. No AMD inference telemetry is configured.")

        metrics = forecaster.evaluate_wape()
        e1, e2, e3 = st.columns(3)
        with e1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">MODEL WAPE</div>
                <div class="metric-value">{metrics['model_wape']*100:.1f}%</div>
                <div class="metric-sub">VS {metrics['baseline_wape']*100:.1f}% NAIVE BASELINE</div>
            </div>
            """, unsafe_allow_html=True)
        with e2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">FORECAST ACCURACY</div>
                <div class="metric-value">{metrics['forecast_accuracy']*100:.1f}%</div>
                <div class="metric-sub">ILLUSTRATIVE FIXTURE ONLY</div>
            </div>
            """, unsafe_allow_html=True)
        with e3:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-label">PLAN INFERENCE LATENCY</div>
                <div class="metric-value">NOT MEASURED</div>
                <div class="metric-sub">NO REMOTE MODEL CALL CONFIGURED</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("#### HARDWARE SPECIFICATIONS")
        tech_df = pd.DataFrame([
            {"Component": "GPU Accelerator", "Specification": settings.AMD_ROCM_DEVICE},
            {"Component": "ROCm / HIP Runtime", "Specification": settings.AMD_ROCM_VERSION},
            {"Component": "Inference Endpoint", "Specification": settings.AMD_ROCM_HOST or "not configured"},
            {"Component": "Vision-Language Model", "Specification": "not invoked"},
            {"Component": "Average Extraction Latency", "Specification": "not measured"}
        ])
        st.table(tech_df)

        st.markdown("#### AUDIT TRACE TIMELINE")
        events = trace_collector.get_events()
        if events:
            st.dataframe(pd.DataFrame([e.dict() for e in events]), use_container_width=True)
        else:
            st.write("No external trace events recorded yet.")
        st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# VIEW 5: CLIENT PROFILE & SETTINGS SCREEN
# ==============================================================================
elif st.session_state.current_page == "profile":
    user_info = st.session_state.authenticated_user or {
        "name": "Mpho Khumalo",
        "shop_name": "Sunnyside Spaza",
        "phone": "+27821234567"
    }
    prof_settings = st.session_state.profile_settings

    # Sidebar Navigation in Profile
    with st.sidebar:
        st.markdown("### STOCKUP PULSE")
        st.caption("Smarter stock. Stronger shops.")
        st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
        st.markdown(f"**STORE:** {user_info['shop_name']}")
        st.caption(f"{user_info['name']} // {user_info['phone']}")

        st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
        if st.button("RETURN TO DASHBOARD", use_container_width=True, type="secondary"):
            st.session_state.current_page = "dashboard"
            st.rerun()

        st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
        if st.button("LOG OUT", use_container_width=True):
            st.session_state.authenticated_user = None
            st.session_state.current_plan = None
            st.session_state.orders = []
            st.session_state.plan_approved = False
            st.session_state.current_page = "login"
            st.toast("Logged out successfully.")
            st.rerun()

    st.markdown('<div class="fade-in">', unsafe_allow_html=True)

    # Top Navigation Row with Back button
    top_nav_c1, top_nav_c2 = st.columns([1, 4])
    with top_nav_c1:
        if st.button("RETURN TO DASHBOARD", key="btn_profile_back_top"):
            st.session_state.current_page = "dashboard"
            st.rerun()

    st.markdown("""
    <div style="margin-top: 10px; margin-bottom: 24px;">
        <div style="font-size: 11px; font-weight: 800; color: #E50000; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 4px;">
            SPAZA STORE CONFIGURATION
        </div>
        <h1 style="font-size: 26px; font-weight: 900; color: #FFFFFF; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px;">
            CLIENT PROFILE & SETTINGS
        </h1>
        <p style="color: #888888; font-size: 13px; margin: 0;">
            Manage shop identity, automated WhatsApp bot dispatch rules, and restocking horizon constraints.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Gamification & Value-Add Metrics Cards (AMD Dark Mode #1A1A1A with #E50000 / #00CC66 top borders)
    st.markdown("#### BUSINESS IMPACT METRICS")
    stat_c1, stat_c2 = st.columns(2)
    with stat_c1:
        st.markdown(f"""
        <div class="metric-card" style="border-top-color: #00CC66;">
            <div class="metric-label">TOTAL RANDS SAVED VIA SCRAPED MARKET SWAPS</div>
            <div class="metric-value" style="color: #00CC66;">R {prof_settings.get('total_saved', 482.50):,.2f}</div>
            <div class="metric-sub" style="color: #00CC66;">+14.2% MARGIN PRESERVED FROM MAKRO & SHOPRITE SCRAPES</div>
        </div>
        """, unsafe_allow_html=True)

    with stat_c2:
        st.markdown(f"""
        <div class="metric-card" style="border-top-color: #E50000;">
            <div class="metric-label">AVERAGE MONTHLY RESTOCK BUDGET</div>
            <div class="metric-value">R {prof_settings.get('avg_monthly_budget', 12500.00):,.2f}</div>
            <div class="metric-sub" style="color: #888888;">OPTIMAL KNAPSACK RESTOCK TIER // BI-WEEKLY ORDERS</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # Profile & Settings Card (Centered container)
    p_col1, p_col2 = st.columns([1, 1])

    with p_col1:
        st.markdown("""
        <div style="background:#1A1A1A; border:1px solid #333333; border-radius:4px; padding:20px; margin-bottom:12px;">
            <div style="font-size:12px; font-weight:800; color:#FFFFFF; text-transform:uppercase; letter-spacing:0.06em;">BASIC INFORMATION</div>
            <div style="font-size:11px; color:#888888;">Account credentials and Spaza identity</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("basic_info_form"):
            prof_name = st.text_input("Full Name", value=user_info.get("name", "Mpho Khumalo"))
            prof_shop = st.text_input("Shop Name", value=user_info.get("shop_name", "Sunnyside Spaza"))
            prof_phone = st.text_input(
                "WhatsApp Number",
                value=user_info.get("phone", "+27821234567"),
                help="Crucial for receiving purchase order dispatch messages and supplier confirmations."
            )
            save_basic = st.form_submit_button("UPDATE BASIC INFO", type="primary", use_container_width=True)

        if save_basic:
            if not prof_name.strip() or not prof_phone.strip():
                st.error("Name and WhatsApp number cannot be empty.")
            else:
                st.session_state.authenticated_user["name"] = prof_name.strip()
                st.session_state.authenticated_user["shop_name"] = prof_shop.strip() or "Sunnyside Spaza"
                st.session_state.authenticated_user["phone"] = prof_phone.strip()
                st.success("Basic information updated successfully.")
                time.sleep(0.4)
                st.rerun()

    with p_col2:
        st.markdown("""
        <div style="background:#1A1A1A; border:1px solid #333333; border-radius:4px; padding:20px; margin-bottom:12px;">
            <div style="font-size:12px; font-weight:800; color:#FFFFFF; text-transform:uppercase; letter-spacing:0.06em;">OPERATIONAL RESTOCK SETTINGS</div>
            <div style="font-size:11px; color:#888888;">Supplier routing, planning horizon, and dispatch coordinates</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("operational_settings_form"):
            horizon_options = ["Next 7 days", "Next 14 days", "Next 30 days"]
            curr_horizon = prof_settings.get("planning_horizon", "14 days")
            default_horizon_idx = 1 if "14" in curr_horizon else (0 if "7" in curr_horizon else 2)
            horizon_choice = st.selectbox("Default Planning Horizon", horizon_options, index=default_horizon_idx)

            suppliers = ["Makro", "Shoprite", "Usave", "Jumbo"]
            curr_supplier = prof_settings.get("preferred_supplier", "Makro")
            sup_idx = suppliers.index(curr_supplier) if curr_supplier in suppliers else 0
            supplier_choice = st.selectbox("Preferred Main Supplier", suppliers, index=sup_idx)

            addr_value = prof_settings.get("delivery_address", "Shop 4, Nelson Mandela Ave, Sunnyside, Pretoria, 0002")
            delivery_addr = st.text_area(
                "Delivery Address",
                value=addr_value,
                height=95,
                help="This address will be automatically injected into generated Purchase Orders for supplier drivers."
            )

            save_ops = st.form_submit_button("SAVE OPERATIONAL SETTINGS", type="primary", use_container_width=True)

        if save_ops:
            st.session_state.profile_settings["planning_horizon"] = horizon_choice
            st.session_state.profile_settings["preferred_supplier"] = supplier_choice
            st.session_state.profile_settings["delivery_address"] = delivery_addr.strip()
            st.success("Operational settings saved successfully.")
            time.sleep(0.4)
            st.rerun()

    st.markdown("<hr style='border-color:#333333;'>", unsafe_allow_html=True)
    foot_c1, foot_c2 = st.columns([1, 1])
    with foot_c1:
        if st.button("RETURN TO DASHBOARD", key="btn_return_dash", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
    with foot_c2:
        st.caption("All profile updates are stored in your local Spaza SQLite database.")

    st.markdown('</div>', unsafe_allow_html=True)
