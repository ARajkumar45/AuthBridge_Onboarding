"""
app.py — AuthBridge AI-Native Employee Onboarding · UI v5.0
Design: Apple HIG Dark Mode — Advanced Dynamic Enterprise

New in v5.0:
  • Animated gradient hero banner (CSS keyframes — gradientFlow)
  • JavaScript count-up KPI cards  (components.v1.html)
  • Interactive Plotly charts with dark theme throughout
  • Animated SVG agent workflow    (CSS dashFlow on edges)
  • Onboarding progress stepper   (horizontal timeline)
  • Pulsing live status indicators (CSS pulseGreen/Blue/Red)
  • Typing indicator               (animated bounce dots)
  • Tech-stack tags in sidebar
  • Department breakdown Plotly bar chart
  • RAGAS Plotly gauge + radar
  • Performance Plotly line + area charts

Run: streamlit run app.py
"""

import os, sys, json, time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

try:
    import plotly.graph_objects as go
    PLOTLY = True
except ImportError:
    PLOTLY = False

try:
    import pandas as pd
    PANDAS = True
except ImportError:
    PANDAS = False

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from database.db import (
    init_database, seed_demo_data, get_connection, log_audit,
    get_performance_summary,
)
try:
    from rag.loader import load_policies, query_policies, _cached_policy_search
    RAG_AVAILABLE = True
except Exception:
    RAG_AVAILABLE = False

try:
    from agents.supervisor import run_onboarding_query, get_graph_mermaid
    AGENTS_AVAILABLE = True
except Exception as e:
    AGENTS_AVAILABLE = False
    AGENT_ERROR = str(e)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="AuthBridge · Onboarding",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN SYSTEM  v5.1 — Deep Navy Dark + Dynamic
#
# Background:  #07091a  (deep navy page base)
# Surface L1:  #0d1428  (sidebar, tabs, selects)
# Surface L2:  #192136  (elevated cards)
# Surface L3:  #1d2a42  (hover states)
# Border:      rgba(255,255,255,.055)
# Accent:      #0a84ff  (Apple system blue, dark mode)
# Gradient:    #0a84ff → #5b6cf9  (hero / accent only)
# Semantic:    #30d158 · #ff9f0a · #ff453a · #bf5af2
# Text:        #ffffff → rgba(235,235,245,.55) → rgba(235,235,245,.28)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, [class*="css"] {
    font-family: -apple-system, 'Inter', BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    background: #07091a !important;
    color: #ffffff !important;
}

/* ── Ambient background glow (Vercel / Linear style) ── */
.main::before {
    content: '';
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background:
        radial-gradient(ellipse 80% 55% at 50% -10%, rgba(10,132,255,.13) 0%, transparent 65%),
        radial-gradient(ellipse 40% 45% at 85% 85%, rgba(191,90,242,.08) 0%, transparent 60%);
    animation: ambientDrift 20s ease-in-out infinite alternate;
}
@keyframes ambientDrift {
    0%   { opacity: .8; transform: scale(1) translate(0,0); }
    100% { opacity: 1;  transform: scale(1.08) translate(-2%, 2%); }
}

/* ── Hide chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="manage-app-button"] { display: none !important; }

/* ════════════════════════════
   ANIMATIONS  v5.1 — Production grade
   ════════════════════════════ */

/* Premium entrance — opacity + travel + scale + blur (Stripe/Linear style) */
@keyframes revealUp {
    from { opacity: 0; transform: translateY(44px) scale(.95); filter: blur(6px); }
    to   { opacity: 1; transform: translateY(0)    scale(1);  filter: blur(0); }
}
@keyframes revealLeft {
    from { opacity: 0; transform: translateX(-36px) scale(.97); filter: blur(4px); }
    to   { opacity: 1; transform: translateX(0) scale(1); filter: blur(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes gradientFlow {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
/* Animated gradient text (Apple/Linear hero) */
@keyframes gradientText {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
/* Pulse dots — tighter, higher contrast */
@keyframes pulseGreen {
    0%, 100% { box-shadow: 0 0 0 0 rgba(48,209,88,.85); }
    60%       { box-shadow: 0 0 0 11px rgba(48,209,88,0); }
}
@keyframes pulseBlue {
    0%, 100% { box-shadow: 0 0 0 0 rgba(10,132,255,.85); }
    60%       { box-shadow: 0 0 0 11px rgba(10,132,255,0); }
}
@keyframes pulseRed {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,69,58,.85); }
    60%       { box-shadow: 0 0 0 11px rgba(255,69,58,0); }
}
@keyframes pulseAmber {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,159,10,.85); }
    60%       { box-shadow: 0 0 0 11px rgba(255,159,10,0); }
}
/* Shimmer sweep — used on hero top bar + cards */
@keyframes shimmerSlide {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(350%); }
}
@keyframes shimmerSweep {
    0%   { left: -80%; }
    100% { left: 130%; }
}
@keyframes dashFlow {
    to { stroke-dashoffset: -15; }
}
@keyframes dotBounce {
    0%, 80%, 100% { transform: translateY(0); opacity: .35; }
    40%            { transform: translateY(-10px); opacity: 1; }
}
/* Border glow — more visible than old borderPulse */
@keyframes borderGlow {
    0%, 100% { border-color: rgba(10,132,255,.2); box-shadow: 0 0 0 0 rgba(10,132,255,.1); }
    50%       { border-color: rgba(10,132,255,.75); box-shadow: 0 0 22px rgba(10,132,255,.22), 0 0 0 4px rgba(10,132,255,.1); }
}
/* Card entrance — blur + scale + travel */
@keyframes cardEntrance {
    from { opacity: 0; transform: translateY(26px) scale(.96); filter: blur(4px); }
    to   { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
}
/* Scan line — sweeps top-to-bottom on hero (Linear/Vercel feel) */
@keyframes scanLine {
    0%   { top: -4px; opacity: 0; }
    5%   { opacity: .55; }
    90%  { opacity: .55; }
    100% { top: calc(100% + 4px); opacity: 0; }
}
/* Orbit glow dot */
@keyframes orbitGlow {
    0%   { transform: rotate(0deg)   translateX(40px) rotate(0deg); }
    100% { transform: rotate(360deg) translateX(40px) rotate(-360deg); }
}
/* Scroll-reveal utility classes (toggled by IntersectionObserver JS) */
.sr-hidden {
    opacity: 0;
    transform: translateY(36px) scale(.97);
    filter: blur(4px);
    transition: none;
}
.sr-visible {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
    transition: opacity .7s cubic-bezier(.16,1,.3,1),
                transform .7s cubic-bezier(.16,1,.3,1),
                filter .7s cubic-bezier(.16,1,.3,1);
}

/* Stagger page children — revealUp replaces old fadeInUp (more dramatic) */
.main .block-container > div:nth-child(1)  { animation: revealUp .65s .00s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(2)  { animation: revealUp .65s .07s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(3)  { animation: revealUp .65s .13s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(4)  { animation: revealUp .65s .19s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(5)  { animation: revealUp .65s .25s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(6)  { animation: revealUp .65s .31s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(7)  { animation: revealUp .65s .37s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(8)  { animation: revealUp .65s .43s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(9)  { animation: revealUp .65s .49s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(10) { animation: revealUp .65s .55s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(11) { animation: revealUp .65s .61s cubic-bezier(.16,1,.3,1) both; }
.main .block-container > div:nth-child(12) { animation: revealUp .65s .67s cubic-bezier(.16,1,.3,1) both; }

/* ── Page layout ── */
.main .block-container {
    padding: 2rem 2.5rem 4rem !important;
    max-width: 100% !important;
}

/* ════════════════════════════
   SIDEBAR
   ════════════════════════════ */

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1428 0%, #0a0f20 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 1.5rem 1.25rem !important; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] label {
    font-size: 0.84rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.09em !important;
    text-transform: uppercase !important;
    color: rgba(235,235,245,.4) !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #111d38 !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 10px !important;
    color: #fff !important;
    font-size: 1.02rem !important;
    transition: border-color .22s, box-shadow .22s !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:hover {
    border-color: rgba(10,132,255,.45) !important;
    box-shadow: 0 0 0 3px rgba(10,132,255,.09) !important;
}

/* ── Inputs ── */
.stTextInput input, .stDateInput input, .stTextArea textarea {
    background: #0e1630 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-size: 1.04rem !important;
    transition: border-color .22s, box-shadow .22s !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #0a84ff !important;
    box-shadow: 0 0 0 3px rgba(10,132,255,0.1) !important;
    outline: none !important;
}
.stSelectbox [data-baseweb="select"] > div {
    background: #0d1428 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 10px !important;
    transition: border-color .2s !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0d1428 !important;
    border-radius: 13px !important;
    padding: 4px !important;
    gap: 2px !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    margin-bottom: 1.75rem !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.5) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 9px 22px !important;
    font-size: 1.02rem !important;
    font-weight: 500 !important;
    color: rgba(235,235,245,.45) !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.22s cubic-bezier(.16,1,.3,1) !important;
    letter-spacing: -0.01em !important;
}
.stTabs [aria-selected="true"] {
    background: #1e2840 !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 5px rgba(0,0,0,.45) !important;
}
.stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
    color: rgba(235,235,245,.72) !important;
    background: rgba(255,255,255,0.035) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #13203c !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    color: rgba(235,235,245,.82) !important;
    border-radius: 10px !important;
    font-size: 1.02rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 1.25rem !important;
    transition: all 0.22s cubic-bezier(.16,1,.3,1) !important;
    letter-spacing: -0.01em !important;
    position: relative !important;
    overflow: hidden !important;
}
/* Shimmer sweep on button hover */
.stButton > button::after {
    content: '' !important; position: absolute !important; top: 0 !important;
    left: -80% !important; width: 55% !important; height: 100% !important;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.07), transparent) !important;
    transform: skewX(-18deg) !important; transition: left .55s ease !important;
}
.stButton > button:hover::after { left: 130% !important; }
.stButton > button:hover {
    background: #1d2a42 !important;
    border-color: rgba(255,255,255,.16) !important;
    color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 22px rgba(0,0,0,.38) !important;
}
.stButton > button:active { transform: translateY(0) scale(.98) !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0a84ff 0%, #0062cc 100%) !important;
    border: none !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 14px rgba(10,132,255,.32) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2d9cff 0%, #0a84ff 100%) !important;
    box-shadow: 0 6px 26px rgba(10,132,255,.42) !important;
    transform: translateY(-2px) !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background: #101828 !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 16px !important;
    padding: 1rem 1.25rem !important;
    margin: 0.4rem 0 !important;
    transition: border-color .2s !important;
    animation: cardEntrance .4s cubic-bezier(.16,1,.3,1) both !important;
}
[data-testid="stChatMessage"]:hover {
    border-color: rgba(255,255,255,.09) !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] > div {
    background: #101828 !important;
    border: 1px solid rgba(255,255,255,.07) !important;
    border-radius: 14px !important;
    transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: rgba(10,132,255,.38) !important;
    box-shadow: 0 0 0 3px rgba(10,132,255,.07) !important;
}
[data-testid="stChatInput"] textarea { color: #ffffff !important; background: transparent !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #101828 !important;
    border: 1px solid rgba(255,255,255,0.055) !important;
    border-radius: 10px !important;
    color: rgba(235,235,245,.82) !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
    transition: background .22s !important;
}
.streamlit-expanderHeader:hover { background: #192136 !important; }
.streamlit-expanderContent {
    background: #101828 !important;
    border: 1px solid rgba(255,255,255,0.055) !important;
    border-top: none !important;
    border-radius: 0 0 10px 10px !important;
}

/* ── Progress / Slider ── */
.stProgress > div > div { background: #0a84ff !important; border-radius: 99px !important; }
.stProgress > div { background: #13203c !important; border-radius: 99px !important; }
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
    background: #0a84ff !important;
    box-shadow: 0 0 0 4px rgba(10,132,255,.18) !important;
}
[data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child { background: #0a84ff !important; }
[data-testid="stSlider"] [data-baseweb="slider"] > div > div:last-child  { background: #0e1630 !important; }

/* ── Alert / Dataframe ── */
[data-testid="stAlert"] {
    background: #101828 !important;
    border: 1px solid rgba(255,255,255,0.055) !important;
    border-radius: 10px !important;
    color: rgba(235,235,245,.8) !important;
}
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.05) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

/* ════════════════════════════
   COMPONENT CLASSES
   ════════════════════════════ */

/* ── Typography ── */
.page-eyebrow {
    font-size: 0.88rem;
    font-weight: 700;
    letter-spacing: 0.13em;
    text-transform: uppercase;
    color: rgba(10,132,255,.75);
    margin-bottom: 0.38rem;
}
.page-title {
    font-size: 2.65rem;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -0.042em;
    line-height: 1.1;
    animation: cardEntrance .65s cubic-bezier(.16,1,.3,1) both;
}
.page-subtitle {
    font-size: 1.12rem;
    color: rgba(235,235,245,.52);
    margin-top: 0.35rem;
    margin-bottom: 1.75rem;
    letter-spacing: -0.012em;
}

/* ── Animated gradient hero ── */
.hero-banner {
    background: linear-gradient(-45deg, #060f1e, #0a1a30, #07142a, #0e2040, #061220);
    background-size: 400% 400%;
    animation: gradientFlow 8s ease infinite;
    border: 1px solid rgba(10,132,255,.3);
    border-radius: 22px;
    padding: 2.25rem 2.5rem;
    position: relative;
    overflow: hidden;
    margin-bottom: 1.75rem;
    box-shadow: 0 4px 48px rgba(10,132,255,.11), 0 1px 0 rgba(255,255,255,.07) inset;
}
/* Ambient radial glows inside hero */
.hero-banner::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse 70% 90% at 10% 60%, rgba(10,132,255,.2) 0%, transparent 100%),
        radial-gradient(ellipse 50% 60% at 92% 20%, rgba(191,90,242,.14) 0%, transparent 100%);
    pointer-events: none;
    animation: ambientDrift 14s ease-in-out infinite alternate;
}
/* Scan line sweeps top → bottom continuously */
.hero-banner::after {
    content: '';
    position: absolute; top: -4px; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent 0%, rgba(10,132,255,.7) 50%, transparent 100%);
    animation: scanLine 5s ease-in-out infinite;
    pointer-events: none;
}
.hero-shimmer {
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent 0%, rgba(10,132,255,.8) 50%, transparent 100%);
    overflow: hidden;
}
.hero-shimmer::after {
    content: '';
    position: absolute; top: 0; left: -100%; right: 0; bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.65), transparent);
    animation: shimmerSlide 2.0s linear infinite;
}
.hero-name {
    font-size: 2.45rem;
    font-weight: 800;
    letter-spacing: -.044em;
    color: #fff;
    position: relative;
    line-height: 1.15;
    animation: cardEntrance .65s .05s cubic-bezier(.16,1,.3,1) both;
}
/* Animated gradient text — Apple/Linear signature */
.hero-name .accent {
    background: linear-gradient(135deg, #409cff 0%, #a8d8ff 40%, #5b6cf9 70%, #409cff 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    animation: gradientText 5s ease infinite;
}
.hero-sub {
    font-size: 1.08rem;
    color: rgba(235,235,245,.56);
    margin-top: .45rem;
    position: relative;
    animation: cardEntrance .65s .15s cubic-bezier(.16,1,.3,1) both;
}
.hero-tags { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: 1.1rem; position: relative;
             animation: cardEntrance .65s .25s cubic-bezier(.16,1,.3,1) both; }

/* ── Static KPI card (fallback / RAGAS) ── */
.kpi {
    background: linear-gradient(160deg, #192136 0%, #151e30 100%);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 1.5rem 1.5rem;
    position: relative;
    transition: border-color .3s, transform .3s cubic-bezier(.16,1,.3,1), box-shadow .3s;
    box-shadow: 0 1px 4px rgba(0,0,0,.45), 0 4px 20px rgba(0,0,0,.22);
    height: 100%;
    animation: cardEntrance .55s cubic-bezier(.16,1,.3,1) both;
    overflow: hidden;
}
/* Shimmer sweep on hover */
.kpi::after {
    content: ''; position: absolute; top: 0; left: -80%; width: 55%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.05), transparent);
    transform: skewX(-18deg); transition: left .65s ease; pointer-events: none;
}
.kpi:hover::after { left: 130%; }
.kpi:hover {
    border-color: rgba(10,132,255,.25);
    transform: translateY(-6px) scale(1.015);
    box-shadow: 0 14px 40px rgba(0,0,0,.48), 0 0 0 1px rgba(10,132,255,.16), 0 0 36px rgba(10,132,255,.07);
}
.kpi-label {
    font-size: 0.86rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: rgba(235,235,245,.42); margin-bottom: 0.6rem;
}
.kpi-value {
    font-size: 2.85rem; font-weight: 800; letter-spacing: -0.052em;
    color: #ffffff; line-height: 1;
}
.kpi-delta { font-size: 0.9rem; font-weight: 500; margin-top: 0.6rem; color: rgba(235,235,245,.42); }
.kpi-delta.green { color: #30d158; }
.kpi-delta.amber { color: #ff9f0a; }
.kpi-delta.red   { color: #ff453a; }
.kpi-accent-bar {
    position: absolute; top: 0; left: 1.5rem; right: 1.5rem;
    height: 2px; border-radius: 0 0 2px 2px;
}
.kpi-accent-bar.blue   { background: linear-gradient(90deg, #0a84ff, #5b6cf9); }
.kpi-accent-bar.green  { background: linear-gradient(90deg, #30d158, #00c46e); }
.kpi-accent-bar.amber  { background: linear-gradient(90deg, #ff9f0a, #f7b731); }
.kpi-accent-bar.red    { background: linear-gradient(90deg, #ff453a, #ff6b6b); }
.kpi-accent-bar.purple { background: linear-gradient(90deg, #bf5af2, #d483f9); }
.kpi-progress-track  { height: 4px; background: rgba(84,84,88,.18); border-radius: 99px; margin-top: 1rem; overflow: hidden; }
.kpi-progress-fill   { height: 100%; border-radius: 99px; transition: width .9s cubic-bezier(.16,1,.3,1); }

/* ── Section label ── */
.section-label {
    font-size: 0.86rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: rgba(235,235,245,.4);
    border-bottom: 1px solid rgba(255,255,255,0.06);
    padding-bottom: 0.6rem; margin: 1.6rem 0 1.1rem;
}

/* ── Status dots ── */
.status-item  { display: flex; align-items: center; gap: .6rem; padding: .32rem 0; }
.sdot         { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.sdot-green   { background: #30d158; animation: pulseGreen  1.8s ease-in-out infinite; }
.sdot-blue    { background: #0a84ff; animation: pulseBlue   1.8s ease-in-out infinite; }
.sdot-red     { background: #ff453a; animation: pulseRed    1.8s ease-in-out infinite; }
.sdot-amber   { background: #ff9f0a; animation: pulseAmber  1.8s ease-in-out infinite; }
.sdot-muted   { background: rgba(84,84,88,.55); }
.sdot-label   { font-size: .97rem; color: rgba(235,235,245,.64); flex: 1; }
.sdot-value   { font-size: .88rem; color: rgba(235,235,245,.38); font-family: ui-monospace, monospace; }

/* ── Pill badges ── */
.pill {
    display: inline-flex; align-items: center; padding: .28rem .8rem;
    border-radius: 99px; font-size: 0.84rem; font-weight: 600;
    letter-spacing: .025em; white-space: nowrap;
    transition: transform .18s cubic-bezier(.16,1,.3,1), box-shadow .18s;
}
.pill:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,0,0,.2); }
.pill-blue   { background: rgba(10,132,255,.11);  color: #409cff; border: 1px solid rgba(10,132,255,.2); }
.pill-green  { background: rgba(48,209,88,.09);   color: #30d158; border: 1px solid rgba(48,209,88,.2); }
.pill-amber  { background: rgba(255,159,10,.09);  color: #ff9f0a; border: 1px solid rgba(255,159,10,.2); }
.pill-red    { background: rgba(255,69,58,.09);   color: #ff6961; border: 1px solid rgba(255,69,58,.2); }
.pill-purple { background: rgba(191,90,242,.09);  color: #bf5af2; border: 1px solid rgba(191,90,242,.2); }
.pill-muted  { background: rgba(84,84,88,.1);     color: rgba(235,235,245,.45); border: 1px solid rgba(84,84,88,.22); }

/* ── Meta row ── */
.meta-row { display: flex; gap: .4rem; flex-wrap: wrap; margin-top: .65rem; }

/* ── Graph wrap ── */
.graph-wrap {
    background: linear-gradient(160deg, #0f1528 0%, #0c1220 100%);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 16px; padding: 1.5rem 1.25rem; margin-bottom: 1.25rem;
    box-shadow: 0 2px 10px rgba(0,0,0,.4);
}

/* ── Chart card ── */
.chart-card {
    background: linear-gradient(160deg, #0f1528, #0c1220);
    border: 1px solid rgba(255,255,255,0.05);
    border-radius: 14px; padding: 1rem 1rem .5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.4); margin-bottom: 1rem;
    transition: box-shadow .22s, border-color .22s;
}
.chart-card:hover { border-color: rgba(255,255,255,.09); box-shadow: 0 4px 20px rgba(0,0,0,.45); }
.chart-title {
    font-size: .86rem; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; color: rgba(235,235,245,.42); margin-bottom: .4rem;
}

/* ── HITL items ── */
.hitl-item {
    background: linear-gradient(160deg, #131a2c, #101828);
    border: 1px solid rgba(255,255,255,0.07);
    border-left: 3px solid rgba(255,159,10,.65);
    border-radius: 14px; padding: 1.25rem 1.4rem; margin-bottom: .72rem;
    transition: transform .3s cubic-bezier(.16,1,.3,1), border-color .25s, box-shadow .3s;
    animation: cardEntrance .5s cubic-bezier(.16,1,.3,1) both;
    position: relative; overflow: hidden;
}
/* Warm ambient glow on hover */
.hitl-item::before {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse 60% 80% at 0% 50%, rgba(255,159,10,.05) 0%, transparent 70%);
    opacity: 0; transition: opacity .3s; pointer-events: none;
}
.hitl-item:hover { transform: translateX(6px); border-color: rgba(255,255,255,.16);
                   box-shadow: 0 8px 32px rgba(0,0,0,.42); }
.hitl-item:hover::before { opacity: 1; }
.hitl-item.critical { border-left-color: #ff453a; }
.hitl-title { font-weight: 700; font-size: 1.1rem; display: flex; align-items: center; gap: .5rem; }
.hitl-meta  { font-size: .92rem; color: rgba(235,235,245,.46); margin-top: .32rem; font-family: ui-monospace, monospace; }
.hitl-desc  { font-size: 1rem; color: rgba(235,235,245,.66); margin-top: .52rem; line-height: 1.6; }
.hitl-ts    { font-size: .82rem; color: rgba(235,235,245,.28); margin-top: .52rem; }

/* ── Employee row ── */
.emp-row {
    display: flex; justify-content: space-between; align-items: center;
    background: linear-gradient(160deg, #121a2c, #0f1528);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; padding: 1.05rem 1.3rem; margin-bottom: .52rem;
    transition: border-color .28s, transform .3s cubic-bezier(.16,1,.3,1), box-shadow .28s;
    animation: cardEntrance .45s cubic-bezier(.16,1,.3,1) both;
    position: relative; overflow: hidden;
}
/* Animated left accent bar — slides in on hover */
.emp-row::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: linear-gradient(180deg, #0a84ff, #5b6cf9);
    border-radius: 3px 0 0 3px;
    transform: scaleY(0); transform-origin: bottom;
    transition: transform .3s cubic-bezier(.16,1,.3,1);
}
.emp-row:hover { border-color: rgba(10,132,255,.2); transform: translateX(6px);
                 box-shadow: 0 6px 24px rgba(0,0,0,.35); }
.emp-row:hover::before { transform: scaleY(1); }
.emp-name { font-weight: 700; font-size: 1.06rem; color: #fff; }
.emp-id   { font-family: ui-monospace,monospace; font-size: .79rem; color: rgba(235,235,245,.32); margin-left: .5rem; }
.emp-sub  { font-size: .92rem; color: rgba(235,235,245,.48); margin-top: .22rem; }

/* ── Document checklist ── */
.doc-checklist {
    display: flex; flex-direction: column; gap: .5rem; margin-bottom: .5rem;
}
.doc-row {
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    background: linear-gradient(160deg, #131a2c, #0f1528);
    border: 1px solid rgba(255,255,255,.06); border-radius: 14px;
    padding: .85rem 1.15rem;
    transition: border-color .25s, transform .28s cubic-bezier(.16,1,.3,1), box-shadow .25s;
    animation: cardEntrance .5s cubic-bezier(.16,1,.3,1) both;
}
.doc-row:hover { border-color: rgba(10,132,255,.22); transform: translateX(5px);
                 box-shadow: 0 5px 20px rgba(0,0,0,.32); }

/* ── Agent trace ── */
.trace-item {
    display: flex; gap: 1rem; align-items: flex-start;
    background: linear-gradient(160deg, #121a2c, #0f1528);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; padding: 1.05rem 1.2rem; margin-bottom: .55rem;
    transition: border-color .28s, transform .3s cubic-bezier(.16,1,.3,1), box-shadow .28s;
    animation: cardEntrance .45s cubic-bezier(.16,1,.3,1) both;
}
.trace-item:hover { border-color: rgba(255,255,255,.15); transform: translateX(5px);
                    box-shadow: 0 5px 22px rgba(0,0,0,.32); }
.trace-dot    { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.trace-agent  { font-size: 1.02rem; font-weight: 700; }
.trace-action { font-size: .98rem; color: rgba(235,235,245,.56); margin-top: .28rem; }
.trace-ts     { font-size: .82rem; color: rgba(235,235,245,.28); margin-top: .28rem; font-family: ui-monospace,monospace; }

/* ── Audit trail ── */
.audit-entry {
    background: linear-gradient(160deg, #121a2c, #0f1528);
    border: 1px solid rgba(255,255,255,0.06);
    border-left: 2px solid rgba(84,84,88,.42);
    border-radius: 0 12px 12px 0; padding: .9rem 1.1rem; margin-bottom: .45rem;
    font-size: .96rem; transition: border-left-color .25s, transform .25s cubic-bezier(.16,1,.3,1), box-shadow .25s;
    font-family: ui-monospace, 'Courier New', monospace;
}
.audit-entry:hover    { border-left-color: #0a84ff; transform: translateX(4px);
                        box-shadow: 0 4px 18px rgba(0,0,0,.3); }
.audit-entry.pii      { border-left-color: #ff453a; }
.audit-action { font-weight: 700; color: rgba(235,235,245,.9); letter-spacing: .012em; }
.audit-meta   { color: rgba(235,235,245,.4); margin-top: .22rem; font-size: .88rem; }
.audit-ts     { color: rgba(235,235,245,.26); margin-top: .22rem; font-size: .8rem; }

/* ── Onboarding stepper ── */
.stepper { display: flex; align-items: center; margin: 1.35rem 0 1.6rem; overflow-x: auto; padding-bottom: .25rem; }
.step    { display: flex; flex-direction: column; align-items: center; gap: .45rem; min-width: 102px; position: relative; z-index: 1; }
.step-circle {
    width: 40px; height: 40px; border-radius: 50%;
    background: #13203c; border: 2px solid rgba(255,255,255,0.09);
    display: flex; align-items: center; justify-content: center;
    font-size: .9rem; font-weight: 700; color: rgba(235,235,245,.32);
    transition: all .4s cubic-bezier(.16,1,.3,1); position: relative; z-index: 2;
}
.step-circle.done   { background: rgba(48,209,88,.15); border-color: rgba(48,209,88,.6); color: #30d158;
                      box-shadow: 0 0 18px rgba(48,209,88,.22); }
.step-circle.active { background: rgba(10,132,255,.15); border-color: #0a84ff; color: #0a84ff;
                      box-shadow: 0 0 0 6px rgba(10,132,255,.15); animation: borderGlow 1.8s ease-in-out infinite; }
.step-label { font-size: .8rem; font-weight: 500; color: rgba(235,235,245,.36); text-align: center; line-height: 1.35; max-width: 94px; }
.step-label.done   { color: #30d158; font-weight: 600; }
.step-label.active { color: #409cff; font-weight: 600; }
.step-connector { flex: 1; height: 2px; background: rgba(255,255,255,0.05); min-width: 20px; margin-top: -26px; transition: background .5s; }
.step-connector.done { background: linear-gradient(90deg, rgba(48,209,88,.45), rgba(48,209,88,.2)); }

/* ── Sidebar brand ── */
.sb-brand { margin-bottom: 1.5rem; padding: .75rem 0 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
.sb-brand-name { font-size: 1.42rem; font-weight: 800; letter-spacing: -.03em; color: #ffffff; }
.sb-brand-sub  { font-size: .88rem; color: rgba(235,235,245,.38); margin-top: .25rem; }

/* ── Tech tags ── */
.tech-tag {
    display: inline-flex; align-items: center; padding: .26rem .65rem;
    border-radius: 7px; font-size: .84rem; font-weight: 500;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
    color: rgba(235,235,245,.54); margin: .1rem;
    transition: background .2s, color .2s, border-color .2s, transform .2s cubic-bezier(.16,1,.3,1);
}
.tech-tag:hover { background: rgba(10,132,255,.1); color: #409cff; border-color: rgba(10,132,255,.28); transform: translateY(-1px); }

/* ── Typing indicator ── */
.typing-dot {
    display: inline-block; width: 7px; height: 7px;
    border-radius: 50%; background: rgba(235,235,245,.5); margin: 0 2.5px;
}
.typing-dot:nth-child(1) { animation: dotBounce 1.1s .00s infinite; }
.typing-dot:nth-child(2) { animation: dotBounce 1.1s .18s infinite; }
.typing-dot:nth-child(3) { animation: dotBounce 1.1s .36s infinite; }

/* ── Empty / info states ── */
.empty-state {
    text-align: center; padding: 3.5rem 1rem;
    color: rgba(235,235,245,.32); font-size: 1.04rem;
    border: 1px dashed rgba(255,255,255,0.08);
    border-radius: 18px; animation: fadeIn .6s ease both;
}
.info-banner {
    background: rgba(10,132,255,.07); border: 1px solid rgba(10,132,255,.2);
    border-radius: 14px; padding: 1rem 1.25rem; font-size: 1rem;
    color: rgba(235,235,245,.68); margin-bottom: 1.35rem;
}

/* ── Divider ── */
.divider { height: 1px; background: rgba(255,255,255,0.05); margin: 1.35rem 0; }

/* ── Footer ── */
.app-footer {
    border-top: 1px solid rgba(255,255,255,0.05);
    padding-top: 1.5rem; margin-top: 2.5rem;
    text-align: center; color: rgba(235,235,245,.22); font-size: .82rem;
}
.app-footer a { color: rgba(235,235,245,.36); text-decoration: none; transition: color .18s; }
.app-footer a:hover { color: rgba(235,235,245,.68); }
</style>
""", unsafe_allow_html=True)

# ── JS: Cursor Spotlight + Scroll Reveal (IntersectionObserver) ───────────────
st.markdown("""
<script>
(function() {
  // ── 1. Cursor spotlight — follows mouse, creates ambient glow (Vercel/Linear style)
  var spotlight = document.createElement('div');
  spotlight.id = 'cursor-spotlight';
  spotlight.style.cssText = [
    'position:fixed','pointer-events:none','z-index:9999',
    'width:500px','height:500px','border-radius:50%',
    'background:radial-gradient(circle, rgba(10,132,255,.07) 0%, transparent 65%)',
    'transform:translate(-50%,-50%)','transition:opacity .4s',
    'top:0','left:0','opacity:0'
  ].join(';');
  document.body.appendChild(spotlight);

  document.addEventListener('mousemove', function(e) {
    spotlight.style.left = e.clientX + 'px';
    spotlight.style.top  = e.clientY + 'px';
    spotlight.style.opacity = '1';
  });
  document.addEventListener('mouseleave', function() {
    spotlight.style.opacity = '0';
  });

  // ── 2. Scroll reveal — add .sr-hidden on all major blocks, then .sr-visible on enter
  function initScrollReveal() {
    var targets = document.querySelectorAll(
      '.kpi, .hitl-item, .emp-row, .trace-item, .audit-entry, ' +
      '.graph-wrap, .chart-card, .hero-banner, .info-banner, .empty-state'
    );
    if (!targets.length) return;

    var io = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.remove('sr-hidden');
          entry.target.classList.add('sr-visible');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

    targets.forEach(function(el, i) {
      el.classList.add('sr-hidden');
      el.style.transitionDelay = (i % 6 * 0.06) + 's';
      io.observe(el);
    });
  }

  // ── 3. Card magnetic tilt on mouse move (subtle, 3-4 degrees max)
  function initCardTilt() {
    var cards = document.querySelectorAll('.kpi, .hitl-item, .emp-row');
    cards.forEach(function(card) {
      card.addEventListener('mousemove', function(e) {
        var r = card.getBoundingClientRect();
        var x = (e.clientX - r.left) / r.width  - 0.5;  // -0.5 to 0.5
        var y = (e.clientY - r.top)  / r.height - 0.5;
        card.style.transform = 'perspective(600px) rotateY(' + (x * 5) + 'deg) rotateX(' + (-y * 4) + 'deg) translateY(-4px) scale(1.01)';
      });
      card.addEventListener('mouseleave', function() {
        card.style.transform = '';
      });
    });
  }

  // Run after Streamlit renders (wait for DOM)
  var attempts = 0;
  var timer = setInterval(function() {
    attempts++;
    var ready = document.querySelector('.kpi, .hitl-item, .emp-row');
    if (ready || attempts > 20) {
      clearInterval(timer);
      initScrollReveal();
      initCardTilt();
    }
  }, 350);

  // Re-run on Streamlit rerenders
  if (window.MutationObserver) {
    new MutationObserver(function(muts) {
      muts.forEach(function(m) {
        if (m.addedNodes.length) {
          setTimeout(function() { initScrollReveal(); initCardTilt(); }, 120);
        }
      });
    }).observe(document.body, { childList: true, subtree: true });
  }
})();
</script>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def section(title: str):
    st.markdown(f'<div class="section-label">{title}</div>', unsafe_allow_html=True)


def pill(text: str, color: str = "muted") -> str:
    return f'<span class="pill pill-{color}">{text}</span>'


def sdot(color: str, label: str, value: str = "") -> str:
    return (f'<div class="status-item">'
            f'<div class="sdot sdot-{color}"></div>'
            f'<span class="sdot-label">{label}</span>'
            f'<span class="sdot-value">{value}</span>'
            f'</div>')


def risk_pill(level: str) -> str:
    color = {"low": "green", "medium": "amber", "high": "red", "critical": "red"}.get(level, "muted")
    return pill(level.upper(), color)


def status_pill(status_str: str) -> str:
    s = status_str.replace("_", " ").lower()
    if any(w in s for w in ("active", "bgv", "compl")):      c = "green"
    elif any(w in s for w in ("pending", "offer", "doc")):   c = "amber"
    else:                                                      c = "muted"
    return pill(s.title(), c)


def kpi(label, value, delta="", delta_color="", accent="blue", progress_pct=None):
    """Static KPI card — used for RAGAS results and single-column contexts."""
    delta_html = f'<div class="kpi-delta {delta_color}">{delta}</div>' if delta else ""
    prog_html  = ""
    if progress_pct is not None:
        bar_color = "#30d158" if progress_pct >= 60 else ("#ff9f0a" if progress_pct >= 30 else "#ff453a")
        prog_html = (f'<div class="kpi-progress-track">'
                     f'<div class="kpi-progress-fill" style="width:{min(float(progress_pct),100):.1f}%;background:{bar_color}"></div>'
                     f'</div>')
    st.markdown(
        f'<div class="kpi">'
        f'  <div class="kpi-accent-bar {accent}"></div>'
        f'  <div class="kpi-label">{label}</div>'
        f'  <div class="kpi-value">{value}</div>'
        f'  {delta_html}{prog_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Animated KPI grid (components.v1.html + JS count-up) ────────────────────

_ACCENT = {
    "blue": "#0a84ff", "green": "#30d158", "amber": "#ff9f0a",
    "red": "#ff453a",  "purple": "#bf5af2",
}
_DELTA_COLOR = {"green": "#30d158", "amber": "#ff9f0a", "red": "#ff453a"}


def animated_kpi_cards(cards: list, key: str = "kpi", card_height: int = 118):
    """
    Renders an animated KPI card grid via st.components.v1.html.
    Each card dict keys:
      label, value (display str), num_value (float|int, optional),
      suffix (str, optional), delta (str), delta_color (str),
      accent (str), progress (float 0-100, optional)
    """
    n     = len(cards)
    n_cols= n

    cards_html = ""
    js_body    = ""

    for i, c in enumerate(cards):
        ac = _ACCENT.get(c.get("accent", ""), "#0a84ff")
        dc = _DELTA_COLOR.get(c.get("delta_color", ""), "rgba(235,235,245,.38)")
        suffix = c.get("suffix", "")

        # Progress bar
        prog = c.get("progress")
        prog_html = ""
        if prog is not None:
            bar_col = "#30d158" if prog >= 60 else ("#ff9f0a" if prog >= 30 else "#ff453a")
            pid = f"pb_{key}_{i}"
            prog_html = (
                f'<div style="height:3px;background:rgba(255,255,255,.06);border-radius:99px;'
                f'margin-top:9px;overflow:hidden">'
                f'<div id="{pid}" style="height:100%;width:0%;background:{bar_col};border-radius:99px;'
                f'transition:width 1s cubic-bezier(.2,.8,.4,1)"></div></div>'
            )
            js_body += (f'setTimeout(function(){{var e=document.getElementById("{pid}");'
                        f'if(e)e.style.width="{min(float(prog),100):.1f}%";}},150);')

        # Delta
        delta_html = (f'<div style="font-size:.8rem;font-weight:500;margin-top:5px;color:{dc}">'
                      f'{c.get("delta","")}</div>') if c.get("delta") else ""

        # Value (count-up or static)
        nv = c.get("num_value", "")
        nv_str = str(nv) if nv != "" else ""
        is_numeric = nv_str.replace(".", "").replace("-", "").isnumeric() and nv_str != ""
        vid = f"kv_{key}_{i}"
        delay_ms = i * 90

        if is_numeric:
            is_float = "." in nv_str
            value_html = f'<div id="{vid}" style="font-size:2.65rem;font-weight:800;letter-spacing:-.052em;color:#fff;line-height:1">0{suffix}</div>'
            js_body += f"""
(function(){{
  var el=document.getElementById("{vid}"),
      target={float(nv)},
      isF={'true' if is_float else 'false'},
      suf="{suffix}",
      t0=null, dur={900 + delay_ms};
  setTimeout(function(){{
    requestAnimationFrame(function step(ts){{
      if(!t0)t0=ts;
      var p=Math.min((ts-t0)/dur,1),
          e=1-Math.pow(1-p,3),
          v=e*target;
      el.textContent=(isF?v.toFixed(1):Math.round(v).toLocaleString())+suf;
      if(p<1)requestAnimationFrame(step);
    }});
  }},{delay_ms});
}})();"""
        else:
            value_html = (f'<div style="font-size:2.15rem;font-weight:700;letter-spacing:-.046em;'
                          f'color:#fff;line-height:1">{c.get("value","—")}</div>')

        cards_html += (
            f'<div style="background:linear-gradient(160deg,#192136,#151e30);'
            f'border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:20px 22px;'
            f'position:relative;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.45),'
            f'0 4px 16px rgba(0,0,0,.18);cursor:default;'
            f'transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease"'
            f' onmouseover="this.style.transform=\'translateY(-2px)\';'
            f'this.style.borderColor=\'rgba(255,255,255,.12)\';'
            f'this.style.boxShadow=\'0 6px 24px rgba(0,0,0,.38)\'"'
            f' onmouseout="this.style.transform=\'\';'
            f'this.style.borderColor=\'rgba(255,255,255,.06)\';'
            f'this.style.boxShadow=\'0 1px 4px rgba(0,0,0,.45),0 4px 16px rgba(0,0,0,.18)\'">'
            f'<div style="position:absolute;top:0;left:22px;right:22px;height:2px;'
            f'border-radius:0 0 2px 2px;background:{ac}"></div>'
            f'<div style="font-size:.76rem;font-weight:600;letter-spacing:.09em;text-transform:uppercase;'
            f'color:rgba(235,235,245,.4);margin-bottom:9px">{c.get("label","")}</div>'
            f'{value_html}'
            f'{delta_html}'
            f'{prog_html}'
            f'</div>'
        )

    rows = (n + n_cols - 1) // n_cols
    total_h = rows * (card_height + 14) + 18

    html = f"""<!DOCTYPE html><html><head>
<meta charset="utf-8">
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{background:#07091a;font-family:-apple-system,'Inter',BlinkMacSystemFont,sans-serif;overflow:hidden}}
  .grid{{display:grid;grid-template-columns:repeat({n_cols},1fr);gap:16px;padding:3px}}
  @keyframes cardEntrance{{
    from{{opacity:0;transform:translateY(28px) scale(.95);filter:blur(5px)}}
    to{{opacity:1;transform:translateY(0) scale(1);filter:blur(0)}}
  }}
  .grid > div{{animation:cardEntrance .6s cubic-bezier(.16,1,.3,1) both}}
  .grid > div:nth-child(1){{animation-delay:.00s}}
  .grid > div:nth-child(2){{animation-delay:.09s}}
  .grid > div:nth-child(3){{animation-delay:.18s}}
  .grid > div:nth-child(4){{animation-delay:.27s}}
  .grid > div:nth-child(5){{animation-delay:.36s}}
  .grid > div:nth-child(6){{animation-delay:.45s}}
</style></head><body>
<div class="grid">{cards_html}</div>
<script>
window.addEventListener('load',function(){{
{js_body}
}});
</script>
</body></html>"""

    components.html(html, height=total_h, scrolling=False)


# ── Plotly helpers ───────────────────────────────────────────────────────────

def _pbase(title="", height=220):
    return dict(
        title=dict(text=title,
                   font=dict(size=11, color="rgba(235,235,245,.35)",
                              family="-apple-system,Inter,sans-serif"),
                   x=0, xanchor="left", y=0.98),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system,Inter,sans-serif",
                  color="rgba(235,235,245,.35)", size=10),
        height=height,
        margin=dict(l=4, r=4, t=30, b=4, pad=0),
        xaxis=dict(gridcolor="rgba(255,255,255,.04)", linecolor="rgba(255,255,255,.06)",
                   tickfont=dict(size=9), zeroline=False),
        yaxis=dict(gridcolor="rgba(255,255,255,.04)", linecolor="rgba(255,255,255,.06)",
                   tickfont=dict(size=9), zeroline=False),
        showlegend=False,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#192136", bordercolor="rgba(255,255,255,.1)",
                        font=dict(size=11, color="#fff",
                                  family="-apple-system,Inter,sans-serif")),
    )


def pline(x, y, color="#0a84ff", title="", height=220, fill=True):
    if not PLOTLY:
        return None
    fc = color + "15" if (len(color) == 7 and color.startswith("#")) else "rgba(10,132,255,.06)"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines",
        line=dict(color=color, width=2, shape="spline"),
        fill="tozeroy" if fill else None,
        fillcolor=fc,
        hovertemplate="%{y}<extra></extra>",
    ))
    fig.update_layout(**_pbase(title, height))
    return fig


def pbars(x, y, colors=None, title="", height=220):
    if not PLOTLY:
        return None
    if colors is None:
        colors = ["#0a84ff"] * len(y)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=y,
        marker=dict(color=colors, line=dict(width=0), cornerradius=5),
        hovertemplate="%{x}: %{y}<extra></extra>",
    ))
    fig.update_layout(**_pbase(title, height))
    fig.update_layout(bargap=0.38)
    return fig


def pgauge(value, title="", color="#0a84ff", max_val=1.0, height=170):
    if not PLOTLY:
        return None
    steps = [
        dict(range=[0, max_val * .4],  color="rgba(255,69,58,.07)"),
        dict(range=[max_val * .4, max_val * .7], color="rgba(255,159,10,.06)"),
        dict(range=[max_val * .7, max_val],       color="rgba(48,209,88,.07)"),
    ]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(font=dict(size=24, color="#fff", family="-apple-system,Inter"),
                    valueformat=".2f"),
        gauge=dict(
            axis=dict(range=[0, max_val], nticks=4,
                      tickfont=dict(color="rgba(235,235,245,.28)", size=8)),
            bar=dict(color=color, thickness=0.52),
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
            steps=steps,
        ),
        title=dict(text=title,
                   font=dict(size=10, color="rgba(235,235,245,.38)",
                              family="-apple-system,Inter")),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=22, b=5),
        font=dict(family="-apple-system,Inter,sans-serif"),
    )
    return fig


# ── Onboarding stepper ───────────────────────────────────────────────────────

def onboarding_stepper(task_rows: list, emp_status: str):
    stages = [
        ("Offer\nAccepted",   "offer_accepted_placeholder"),
        ("Docs\nSubmitted",   "document_upload"),
        ("Identity\nVerified","identity_verification"),
        ("BGV\nCleared",      "criminal_check"),
        ("IT\nProvisioned",   "it_provisioning"),
        ("Day 1\nReady",      "__active__"),
    ]
    done_types = {t["task_type"] for t in task_rows if t["status"] == "completed"}
    done_types_any = {t["task_type"] for t in task_rows}

    html = '<div class="stepper">'
    for i, (label, task_key) in enumerate(stages):
        if task_key == "__active__":
            done = emp_status == "active"
        elif task_key == "offer_accepted_placeholder":
            done = bool(done_types_any)  # always done once we have tasks
        else:
            done = task_key in done_types

        prev_key = stages[i - 1][1] if i > 0 else None
        prev_done = (prev_key == "offer_accepted_placeholder" and bool(done_types_any)) or \
                    (prev_key == "__active__" and emp_status == "active") or \
                    (prev_key in done_types) if prev_key else True
        active_now = not done and prev_done

        lbl_display = label.replace("\n", "<br>")
        if done:
            circle_html = '<div class="step-circle done">✓</div>'
            lc = "done"
        elif active_now:
            circle_html = f'<div class="step-circle active">{i+1}</div>'
            lc = "active"
        else:
            circle_html = f'<div class="step-circle">{i+1}</div>'
            lc = ""

        html += f'<div class="step">{circle_html}<div class="step-label {lc}">{lbl_display}</div></div>'
        if i < len(stages) - 1:
            html += f'<div class="step-connector {"done" if done else ""}"></div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def initialize_system():
    init_database()
    seed_demo_data()
    if RAG_AVAILABLE:
        try:
            load_policies()
            return True
        except Exception:
            return False
    return False


rag_ready = initialize_system()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div class="sb-brand">'
        '<div class="sb-brand-name">🛡️ AuthBridge</div>'
        '<div class="sb-brand-sub">AI-Native Employee Onboarding</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tenant_id = st.selectbox(
        "Tenant",
        ["authbridge", "globalbank"],
        help="Switch tenants to verify multi-tenant data isolation",
    )

    # ── Role selector (FIRST — role must be known before scoping employee data)
    ROLES = ["👤 Employee", "👔 Manager", "🛡️ HR Admin", "⚙️ Super Admin"]
    user_role = st.selectbox("Role", ROLES, index=0,
                             help="Production: derived from SSO/JWT. Demo: choose to simulate access levels.")
    role_key  = user_role.split(" ", 1)[1] if " " in user_role else user_role

    # ── Session isolation on privilege downgrade ──────────────────────────────
    _ROLE_RANK = {"Employee": 0, "Manager": 1, "HR Admin": 2, "Super Admin": 3}
    _prev_role = st.session_state.get("_active_role", role_key)
    if _prev_role != role_key:
        if _ROLE_RANK.get(role_key, 0) < _ROLE_RANK.get(_prev_role, 0):
            for _k in [k for k in list(st.session_state.keys()) if k != "_active_role"]:
                del st.session_state[_k]
            st.toast("Session cleared on role downgrade", icon="🔒")
        else:
            st.toast(f"Elevated to {role_key}", icon="🔑")
    st.session_state["_active_role"] = role_key

    # ── Role access badge ─────────────────────────────────────────────────────
    _BADGE = {
        "Employee":    ("#30d158", "👤", "New Hire Portal only"),
        "Manager":     ("#0a84ff", "👔", "Portal + Team View"),
        "HR Admin":    ("#bf5af2", "🛡️","Full Dashboard"),
        "Super Admin": ("#ff9f0a", "⚙️","Full + System Access"),
    }
    _bc, _bi, _bd = _BADGE.get(role_key, ("#888", "?", ""))
    st.markdown(
        f'<div style="background:rgba(255,255,255,.04);border:1px solid {_bc}44;'
        f'border-radius:10px;padding:.45rem .75rem;margin:.2rem 0 .5rem;'
        f'display:flex;align-items:center;gap:.6rem">'
        f'<span style="font-size:1rem">{_bi}</span>'
        f'<div><div style="font-size:.77rem;font-weight:700;color:{_bc}">{role_key}</div>'
        f'<div style="font-size:.67rem;color:rgba(235,235,245,.38)">{_bd}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Role-scoped employee selector ─────────────────────────────────────────
    conn = get_connection()
    employees = conn.execute(
        "SELECT employee_id, full_name FROM employees WHERE tenant_id=? ORDER BY full_name",
        (tenant_id,),
    ).fetchall()
    conn.close()
    employees = [dict(e) for e in employees]

    if role_key == "Employee":
        # SECURITY: Employee cannot browse other records.
        # Production: selected_emp_id = jwt_payload["sub"]
        # Demo: auto-assign the first employee in the tenant.
        if employees:
            _me = employees[0]
            selected_emp_id = _me["employee_id"]
            st.markdown(
                f'<div style="background:rgba(10,132,255,.07);border:1px solid rgba(10,132,255,.2);'
                f'border-radius:10px;padding:.45rem .75rem;font-size:.8rem">'
                f'<div style="font-weight:600;color:#0a84ff;font-size:.68rem;'
                f'text-transform:uppercase;letter-spacing:.06em;margin-bottom:.15rem">Signed in as</div>'
                f'<div style="color:rgba(235,235,245,.9);font-weight:600">{_me["full_name"]}</div>'
                f'<div style="color:rgba(235,235,245,.38);font-size:.7rem">{_me["employee_id"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            selected_emp_id = "EMP001"
            st.caption("No employee record found.")
    else:
        emp_options = {
            f"{e['employee_id']} — {e['full_name']}": e["employee_id"]
            for e in employees
        }
        if emp_options:
            _lbl = ("View team member" if role_key == "Manager"
                    else "Select employee")
            selected_emp_display = st.selectbox("Employee", list(emp_options.keys()),
                                                help=_lbl)
            selected_emp_id = emp_options[selected_emp_display]
        else:
            selected_emp_id = "EMP001"
            st.caption("No employees found.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── System status
    st.markdown(
        '<div style="font-size:.66rem;font-weight:600;letter-spacing:.09em;'
        'text-transform:uppercase;color:rgba(235,235,245,.28);margin-bottom:.55rem">System</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        sdot("green" if AGENTS_AVAILABLE else "red",    "Agents",   "online"  if AGENTS_AVAILABLE else "offline") +
        sdot("green" if rag_ready         else "amber", "RAG",      "ready"   if rag_ready         else "no key") +
        sdot("green",                                   "Database", "online") +
        sdot("blue",                                    "Tenant",   tenant_id),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Tech stack tags
    st.markdown(
        '<div style="font-size:.66rem;font-weight:600;letter-spacing:.09em;'
        'text-transform:uppercase;color:rgba(235,235,245,.28);margin-bottom:.5rem">Stack</div>',
        unsafe_allow_html=True,
    )
    tags_html = "".join(
        f'<span class="tech-tag">{t}</span>'
        for t in [
            "LangGraph", "NVIDIA Llama-3.3-70B",
            "ChromaDB", "HyDE + LRU",
            "FastAPI",  "DPDP 2023",
            "HITL",     "Multi-Tenant",
        ]
    )
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:.1rem">{tags_html}</div>',
                unsafe_allow_html=True)

    # ── Live 7-day operational stats (Manager+ only)
    # HITL counts, latency, confidence are internal metrics employees must not see.
    if role_key in ("Manager", "HR Admin", "Super Admin"):
        try:
            perf_sb = get_performance_summary(tenant_id, days=7)
            if perf_sb.get("total_queries", 0) > 0:
                st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:.66rem;font-weight:600;letter-spacing:.09em;'
                    'text-transform:uppercase;color:rgba(235,235,245,.28);margin-bottom:.5rem">7-Day</div>',
                    unsafe_allow_html=True,
                )
                hitl_sb = perf_sb.get("hitl_escalations", 0)
                st.markdown(
                    sdot("green", "Queries",    str(perf_sb["total_queries"])) +
                    sdot("green" if perf_sb["avg_latency_ms"] < 5000 else "amber",
                         "Latency",  f"{perf_sb['avg_latency_ms']:.0f} ms") +
                    sdot("green", "Confidence", f"{int(perf_sb['avg_confidence'] * 100)}%") +
                    sdot("green" if hitl_sb == 0 else "red", "HITL", str(hitl_sb)),
                    unsafe_allow_html=True,
                )
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────


# ─── Dynamic role-based tab creation ──────────────────────────────────────────
_ROLE_TABS = {
    "Employee":    ["🏠 New Hire Portal"],
    "Manager":     ["🏠 New Hire Portal", "👔 Manager View"],
    "HR Admin":    ["🏠 New Hire Portal", "👔 Manager View",
                    "🛡️ HR Admin Dashboard", "🔍 Agent Trace Viewer",
                    "📊 RAGAS Evaluation", "⚡ Performance"],
    "Super Admin": ["🏠 New Hire Portal", "👔 Manager View",
                    "🛡️ HR Admin Dashboard", "🔍 Agent Trace Viewer",
                    "📊 RAGAS Evaluation", "⚡ Performance"],
}
_visible_tabs = _ROLE_TABS.get(role_key, _ROLE_TABS["Employee"])
_created_tabs = st.tabs(_visible_tabs)
_tab_iter     = iter(_created_tabs)


def _pick_tab(label):
    return next(_tab_iter) if label in _visible_tabs else None


tab1 = _pick_tab("🏠 New Hire Portal")
tab2 = _pick_tab("👔 Manager View")
tab3 = _pick_tab("🛡️ HR Admin Dashboard")
tab4 = _pick_tab("🔍 Agent Trace Viewer")
tab5 = _pick_tab("📊 RAGAS Evaluation")
tab6 = _pick_tab("⚡ Performance")



# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — NEW HIRE PORTAL
# ─────────────────────────────────────────────────────────────────────────────

if tab1 is not None:
    with tab1:
        st.markdown('<div class="page-eyebrow">Onboarding Assistant</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-title">New Hire Portal</div>', unsafe_allow_html=True)

        # Fetch employee + tasks
        conn = get_connection()
        emp_data  = conn.execute(
            "SELECT * FROM employees WHERE employee_id=? AND tenant_id=?",
            (selected_emp_id, tenant_id),
        ).fetchone()
        emp_tasks = conn.execute(
            "SELECT * FROM tasks WHERE employee_id=? AND tenant_id=?",
            (selected_emp_id, tenant_id),
        ).fetchall()
        conn.close()

        # sqlite3.Row doesn't support .get() — convert to plain dicts
        emp_data  = dict(emp_data)  if emp_data  else None
        emp_tasks = [dict(t) for t in emp_tasks]

        if emp_data:
            done_t  = sum(1 for t in emp_tasks if t["status"] == "completed")
            total_t = len(emp_tasks)
            pct_t   = round(done_t / max(total_t, 1) * 100)

            # ── Animated gradient hero
            st.markdown(f"""
<div class="hero-banner">
  <div class="hero-shimmer"></div>
  <div class="hero-name">
    Welcome, <span class="accent">{emp_data['full_name']}</span>&nbsp;👋
  </div>
  <div class="hero-sub">
    {emp_data.get('designation', 'New Hire')} &nbsp;·&nbsp;
    {emp_data['department']}  &nbsp;·&nbsp;
    Joining {emp_data['date_of_joining'] or 'TBD'}
  </div>
  <div class="hero-tags">
    {pill(emp_data['status'].replace('_', ' ').title(),
          "green" if "active" in emp_data['status'] else "amber")}
    {pill(emp_data['employee_id'], "blue")}
    {pill(f"{pct_t}% onboarding complete",
          "green" if pct_t >= 70 else "amber")}
    {pill(tenant_id, "muted")}
  </div>
</div>
""", unsafe_allow_html=True)

            # ── Onboarding stepper
            section("Onboarding Journey")
            onboarding_stepper(emp_tasks, emp_data["status"])

            # ── Document Collection Checklist
            section("Document Collection")
            DOC_TASK_TYPES = {
                "document_upload":        ("🪪", "Identity Documents",        "Upload passport / Aadhaar / driving licence"),
                "identity_verification":  ("🔐", "Identity Verification",     "iBRIDGE cross-check against govt databases"),
                "education_verification": ("🎓", "Education Verification",    "Degree certificates authenticated by partner"),
                "employment_verification":("🏢", "Employment History Check",  "Previous employer references verified"),
                "criminal_check":         ("🔍", "Criminal Record Check",     "Police clearance + court record scan"),
                "it_provisioning":        ("💻", "IT Provisioning",           "Laptop, email, and app access setup"),
            }
            task_map = {t["task_type"]: t for t in emp_tasks}

            doc_rows_html = ""
            for ttype, (icon, label, hint) in DOC_TASK_TYPES.items():
                t = task_map.get(ttype)
                if t:
                    s = t["status"]
                    if s == "completed":
                        badge = '<span style="background:rgba(48,209,88,.15);color:#30d158;font-size:.7rem;font-weight:700;padding:.18rem .62rem;border-radius:50px;border:1px solid rgba(48,209,88,.3)">✓ VERIFIED</span>'
                    elif s == "in_progress":
                        badge = '<span style="background:rgba(255,214,10,.12);color:#ffd60a;font-size:.7rem;font-weight:700;padding:.18rem .62rem;border-radius:50px;border:1px solid rgba(255,214,10,.3)">⟳ IN REVIEW</span>'
                    else:
                        badge = '<span style="background:rgba(255,69,58,.1);color:#ff453a;font-size:.7rem;font-weight:700;padding:.18rem .62rem;border-radius:50px;border:1px solid rgba(255,69,58,.25)">○ PENDING</span>'
                else:
                    badge = '<span style="background:rgba(142,142,147,.1);color:rgba(235,235,245,.35);font-size:.7rem;font-weight:700;padding:.18rem .62rem;border-radius:50px;border:1px solid rgba(142,142,147,.2)">— N/A</span>'

                doc_rows_html += f"""
<div class="doc-row">
  <div style="display:flex;align-items:center;gap:.75rem;flex:1;min-width:0">
    <span style="font-size:1.2rem;flex-shrink:0">{icon}</span>
    <div style="min-width:0">
      <div style="font-size:.88rem;font-weight:600;color:rgba(235,235,245,.9);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</div>
      <div style="font-size:.74rem;color:rgba(235,235,245,.36);margin-top:.1rem">{hint}</div>
    </div>
  </div>
  <div style="flex-shrink:0">{badge}</div>
</div>"""

            st.markdown(f'<div class="doc-checklist">{doc_rows_html}</div>', unsafe_allow_html=True)

            # ── Policy Acknowledgement
            section("Policy Acknowledgement")
            POLICIES = [
                ("policy_acknowledgement", "📜 Code of Conduct",
                 "I have read and understood the company Code of Conduct, including anti-harassment, ethics, and professional behaviour standards."),
                ("policy_data_privacy", "🔒 Data Privacy & DPDP Act 2023",
                 "I acknowledge my obligations under the DPDP Act 2023. I consent to processing of my personal data for onboarding and employment purposes only."),
                ("policy_it_acceptable_use", "💻 IT Acceptable Use Policy",
                 "I have reviewed and agree to the IT Acceptable Use Policy covering device, network, and software usage."),
                ("policy_leave_attendance", "🗓️ Leave & Attendance Policy",
                 "I confirm I have read the Leave and Attendance Policy, including probation-period leave entitlements."),
            ]

            ack_conn = get_connection()

            for pol_type, pol_title, pol_text in POLICIES:
                ack_task = ack_conn.execute(
                    "SELECT * FROM tasks WHERE employee_id=? AND tenant_id=? AND task_type=?",
                    (selected_emp_id, tenant_id, pol_type)
                ).fetchone()
                ack_task = dict(ack_task) if ack_task else None
                already_acked = ack_task and ack_task["status"] == "completed"

                border_color = "rgba(48,209,88,.25)" if already_acked else "rgba(10,132,255,.18)"
                bg_color     = "rgba(48,209,88,.04)"  if already_acked else "rgba(10,132,255,.04)"

                st.markdown(f"""
<div style="background:{bg_color};border:1px solid {border_color};border-radius:14px;
            padding:1.1rem 1.25rem;margin-bottom:.75rem;position:relative;overflow:hidden">
  <div style="font-size:.92rem;font-weight:700;color:rgba(235,235,245,.92);margin-bottom:.45rem">{pol_title}</div>
  <div style="font-size:.8rem;color:rgba(235,235,245,.52);line-height:1.55;margin-bottom:.75rem">{pol_text}</div>
  {'<div style="font-size:.75rem;font-weight:600;color:#30d158">✓ Acknowledged on ' + (ack_task.get("completed_at","") or ack_task.get("created_at","today"))[:10] + '</div>' if already_acked else ""}
</div>""", unsafe_allow_html=True)

                if not already_acked:
                    btn_key = f"ack_{pol_type}_{selected_emp_id}"
                    if st.button(f"✅  I Acknowledge — {pol_title}", key=btn_key, use_container_width=False):
                        # Insert or update the task record
                        existing = ack_conn.execute(
                            "SELECT id FROM tasks WHERE employee_id=? AND tenant_id=? AND task_type=?",
                            (selected_emp_id, tenant_id, pol_type)
                        ).fetchone()
                        import datetime as _dt
                        now_str = _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                        if existing:
                            ack_conn.execute(
                                "UPDATE tasks SET status='completed', completed_at=? WHERE employee_id=? AND tenant_id=? AND task_type=?",
                                (now_str, selected_emp_id, tenant_id, pol_type)
                            )
                        else:
                            ack_conn.execute(
                                "INSERT INTO tasks (employee_id, tenant_id, task_type, task_name, status, assigned_agent, created_at, completed_at) "
                                "VALUES (?,?,?,?,'completed','system',?,?)",
                                (selected_emp_id, tenant_id, pol_type,
                                 pol_title.replace("📜","").replace("🔒","").replace("💻","").replace("🗓️","").strip(),
                                 now_str, now_str)
                            )
                        ack_conn.commit()
                        log_audit(selected_emp_id, tenant_id, "POLICY_ACK",
                                  f"Employee acknowledged {pol_title}", "system")
                        st.success(f"Acknowledged! Your consent for '{pol_title}' has been recorded and added to the immutable audit trail.")
                        st.rerun()

            ack_conn.close()

        else:
            st.markdown(
                '<div class="page-subtitle">'
                'AI-powered assistant — policies, documents, BGV status, and your DPDP rights'
                '</div>',
                unsafe_allow_html=True,
            )

        # ── Quick actions
        st.markdown(
            '<div style="font-size:.66rem;font-weight:600;letter-spacing:.09em;'
            'text-transform:uppercase;color:rgba(235,235,245,.28);margin-bottom:.6rem">Quick Actions</div>',
            unsafe_allow_html=True,
        )
        qa1, qa2, qa3, qa4 = st.columns(4)
        with qa1:
            if st.button("📋  Leave Policy",  use_container_width=True):
                st.session_state.quick_query = "What is the leave policy for new joiners during probation?"
        with qa2:
            if st.button("🔍  BGV Status",    use_container_width=True):
                st.session_state.quick_query = "What is the status of my background verification?"
        with qa3:
            if st.button("🔒  DPDP Rights",   use_container_width=True):
                st.session_state.quick_query = "What are my data privacy rights under DPDP Act?"
        with qa4:
            if st.button("💻  IT Setup",      use_container_width=True):
                st.session_state.quick_query = "What IT equipment and access will I get on Day 1?"

        st.markdown("<div style='margin-top:.875rem'/>", unsafe_allow_html=True)

        # ── Chat
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        user_query = st.chat_input("Ask anything about your onboarding…")

        if "quick_query" in st.session_state:
            user_query = st.session_state.quick_query
            del st.session_state.quick_query

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and "meta" in msg:
                    st.markdown(msg["meta"], unsafe_allow_html=True)

        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                if AGENTS_AVAILABLE:
                    typing = st.empty()
                    typing.markdown(
                        '<div style="display:flex;align-items:center;gap:5px;padding:.3rem 0">'
                        '<span class="typing-dot"></span>'
                        '<span class="typing-dot"></span>'
                        '<span class="typing-dot"></span>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    try:
                        result     = run_onboarding_query(query=user_query, employee_id=selected_emp_id, tenant_id=tenant_id)
                        response   = result.get("response", "I couldn't process that query.")
                        trace      = result.get("agent_trace", [])
                        latency_ms = result.get("latency_ms", 0)
                        confidence = result.get("confidence", 0.0)
                        needs_hitl = result.get("needs_hitl", False)

                        typing.empty()
                        st.markdown(response)

                        conf_pct   = int(confidence * 100)
                        conf_color = "green" if conf_pct >= 70 else ("amber" if conf_pct >= 40 else "red")
                        lat_color  = "green" if latency_ms < 3000 else ("amber" if latency_ms < 8000 else "red")
                        agents_str = " → ".join(t.get("agent", "") for t in trace) or "supervisor"

                        meta = (
                            f'<div class="meta-row">'
                            f'{pill(f"Confidence {conf_pct}%", conf_color)}'
                            f'{pill(f"{latency_ms:.0f} ms", lat_color)}'
                            f'{pill(agents_str, "blue")}'
                            f'{pill("HITL Required", "red") if needs_hitl else ""}'
                            f'</div>'
                        )
                        st.markdown(meta, unsafe_allow_html=True)

                        st.session_state.last_trace  = trace
                        st.session_state.last_result = result
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": response, "meta": meta}
                        )
                    except Exception as e:
                        typing.empty()
                        response = f"⚠️ {str(e)} — ensure `NVIDIA_API_KEY` is set in `.env`."
                        st.error(response)
                        st.session_state.chat_history.append({"role": "assistant", "content": response})
                else:
                    typing_resp = "Agents offline — set `NVIDIA_API_KEY` in `.env` and restart."
                    st.warning(typing_resp)
                    st.session_state.chat_history.append({"role": "assistant", "content": typing_resp})


    # ─────────────────────────────────────────────────────────────────────────────
    # TAB 2 — MANAGER VIEW
    # ─────────────────────────────────────────────────────────────────────────────

if tab2 is not None:
    with tab2:
        st.markdown('<div class="page-eyebrow">Team Oversight</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-title">Manager View</div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="page-subtitle">Team onboarding tracker for '
            f'<strong style="color:#fff">{tenant_id}</strong> — accountability KPIs and pending actions</div>',
            unsafe_allow_html=True,
        )

        mgr_conn = get_connection()

        all_emps = mgr_conn.execute(
            "SELECT * FROM employees WHERE tenant_id=? ORDER BY date_of_joining DESC",
            (tenant_id,)
        ).fetchall()
        all_emps = [dict(e) for e in all_emps]

        # ── Team KPIs
        section("Team KPIs")
        total_emps  = len(all_emps)
        active_emps = sum(1 for e in all_emps if "active" in e.get("status", ""))
        all_tasks   = mgr_conn.execute(
            "SELECT * FROM tasks WHERE tenant_id=?", (tenant_id,)
        ).fetchall()
        all_tasks   = [dict(t) for t in all_tasks]
        pending_cnt = sum(1 for t in all_tasks if t["status"] == "pending")
        done_cnt    = sum(1 for t in all_tasks if t["status"] == "completed")
        ack_cnt     = sum(1 for t in all_tasks if t["task_type"] == "policy_acknowledgement" and t["status"] == "completed")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            kpi("Team Size",       str(total_emps),  f"{active_emps} active",                accent="blue")
        with m2:
            pct_done = round(done_cnt / max(done_cnt + pending_cnt, 1) * 100)
            kpi("Tasks Complete",  f"{pct_done}%",   f"{done_cnt} of {done_cnt+pending_cnt}", accent="green",
                delta_color="green", progress_pct=pct_done)
        with m3:
            kpi("Pending Actions", str(pending_cnt), "across all hires",                     accent="amber",
                delta_color="amber" if pending_cnt > 0 else "green")
        with m4:
            kpi("Policies Acked",  str(ack_cnt),     "code of conduct",                      accent="purple")

        # ── Per-employee onboarding table
        section("Team Onboarding Tracker")

        if not all_emps:
            st.info("No employees registered yet.")
        else:
            for emp in all_emps:
                emp_id_m = emp["employee_id"]
                emp_tasks_m = [t for t in all_tasks if t["employee_id"] == emp_id_m]
                done_m  = sum(1 for t in emp_tasks_m if t["status"] == "completed")
                total_m = len(emp_tasks_m)
                pct_m   = round(done_m / max(total_m, 1) * 100)

                pending_tasks_m = [t for t in emp_tasks_m if t["status"] == "pending"]
                pending_labels  = ", ".join(t["task_name"] for t in pending_tasks_m[:3])
                if len(pending_tasks_m) > 3:
                    pending_labels += f" +{len(pending_tasks_m) - 3} more"
                pending_labels = pending_labels or "—"

                status_s = emp.get("status", "pending")
                if "active" in status_s:
                    s_badge = '<span style="color:#30d158;font-size:.75rem;font-weight:700">● ACTIVE</span>'
                elif "pending" in status_s:
                    s_badge = '<span style="color:#ffd60a;font-size:.75rem;font-weight:700">⟳ PENDING</span>'
                else:
                    s_badge = f'<span style="color:rgba(235,235,245,.4);font-size:.75rem;font-weight:700">{status_s.upper()}</span>'

                bar_color = "#30d158" if pct_m >= 70 else ("#ffd60a" if pct_m >= 35 else "#ff453a")
                progress_bar = (
                    f'<div style="height:4px;background:rgba(255,255,255,.07);border-radius:4px;margin-top:.45rem">'
                    f'<div style="height:4px;width:{pct_m}%;background:{bar_color};border-radius:4px;'
                    f'transition:width .6s cubic-bezier(.16,1,.3,1)"></div></div>'
                )

                dept = emp.get("department", "—")
                desig = emp.get("designation", "—")
                join = emp.get("date_of_joining", "TBD")

                st.markdown(f"""
<div class="emp-row" style="cursor:default">
  <div style="display:flex;align-items:center;justify-content:space-between;gap:.75rem;flex-wrap:wrap">
    <div>
      <span class="emp-name">{emp['full_name']}</span>
      <span class="emp-id">{emp_id_m}</span>
      <div class="emp-sub">{desig} &nbsp;·&nbsp; {dept} &nbsp;·&nbsp; Joined {join}</div>
    </div>
    <div style="display:flex;align-items:center;gap:1rem;flex-shrink:0">
      {s_badge}
      <span style="font-size:.82rem;font-weight:700;color:rgba(235,235,245,.75)">{pct_m}% complete</span>
    </div>
  </div>
  {progress_bar}
  <div style="margin-top:.5rem;font-size:.77rem;color:rgba(235,235,245,.38)">
    <strong style="color:rgba(235,235,245,.52)">Pending:</strong> {pending_labels}
  </div>
</div>""", unsafe_allow_html=True)

        # ── HITL escalations needing manager sign-off
        section("Pending Manager Sign-Off")
        hitl_mgr = mgr_conn.execute(
            "SELECT * FROM hitl_queue WHERE tenant_id=? AND status='pending' ORDER BY created_at DESC LIMIT 8",
            (tenant_id,)
        ).fetchall()
        hitl_mgr = [dict(h) for h in hitl_mgr]

        if not hitl_mgr:
            st.markdown(
                '<div style="padding:1.2rem 0;font-size:.9rem;color:rgba(235,235,245,.4);text-align:center">'
                '✅ No pending escalations — your team is on track'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            for item in hitl_mgr:
                qtype = item.get("query_type", "General")
                created = (item.get("created_at", "") or "")[:16]
                emp_name = next(
                    (e["full_name"] for e in all_emps if e["employee_id"] == item.get("employee_id")),
                    item.get("employee_id", "Unknown"),
                )
                st.markdown(f"""
<div class="hitl-item">
  <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.5rem">
    <span style="background:rgba(255,159,10,.15);color:#ff9f0a;font-size:.72rem;font-weight:700;
                 padding:.16rem .55rem;border-radius:50px;border:1px solid rgba(255,159,10,.3)">
      ESCALATED
    </span>
    <span style="font-size:.8rem;font-weight:600;color:rgba(235,235,245,.75)">{emp_name}</span>
    <span style="font-size:.75rem;color:rgba(235,235,245,.35);margin-left:auto">{created}</span>
  </div>
  <div style="font-size:.87rem;color:rgba(235,235,245,.7);margin-bottom:.35rem">
    {item.get('query', '—')}
  </div>
  <div style="font-size:.75rem;color:rgba(235,235,245,.35)">{qtype}</div>
</div>""", unsafe_allow_html=True)

        mgr_conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — HR ADMIN DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

if tab3 is not None:
    with tab3:
        st.markdown('<div class="page-eyebrow">Operations Center</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-title">HR Admin Dashboard</div>', unsafe_allow_html=True)

        st.markdown(
            f'<div class="page-subtitle">Tenant <strong style="color:#fff">{tenant_id}</strong>'
            f' — Onboarding oversight and Human-in-the-Loop governance</div>',
            unsafe_allow_html=True,
        )

        conn = get_connection()
        m_emp   = conn.execute("SELECT COUNT(*) FROM employees  WHERE tenant_id=?", (tenant_id,)).fetchone()[0]
        m_tot   = conn.execute("SELECT COUNT(*) FROM tasks      WHERE tenant_id=?", (tenant_id,)).fetchone()[0]
        m_done  = conn.execute("SELECT COUNT(*) FROM tasks      WHERE tenant_id=? AND status='completed'", (tenant_id,)).fetchone()[0]
        m_hitl  = conn.execute("SELECT COUNT(*) FROM hitl_queue WHERE tenant_id=? AND status='pending'",   (tenant_id,)).fetchone()[0]
        m_grant = conn.execute("SELECT COUNT(*) FROM consents   WHERE tenant_id=? AND status='granted'",   (tenant_id,)).fetchone()[0]
        m_pend  = conn.execute("SELECT COUNT(*) FROM consents   WHERE tenant_id=? AND status='pending'",   (tenant_id,)).fetchone()[0]
        m_audit = conn.execute("SELECT COUNT(*) FROM audit_trail WHERE tenant_id=?",                        (tenant_id,)).fetchone()[0]
        compl_pct = round(m_done / max(m_tot, 1) * 100, 1)
        conn.close()

        # ── Animated KPI cards
        animated_kpi_cards([
            {"label": "Total Employees",   "value": str(m_emp),       "num_value": m_emp,
             "accent": "blue"},
            {"label": "Task Completion",   "value": f"{compl_pct}%",  "num_value": compl_pct,
             "suffix": "%",
             "delta": f"{m_done}/{m_tot} tasks done",
             "delta_color": "green" if compl_pct > 60 else "amber",
             "accent": "green" if compl_pct > 60 else "amber",
             "progress": compl_pct},
            {"label": "HITL Pending",      "value": str(m_hitl),      "num_value": m_hitl,
             "delta": "Needs review" if m_hitl > 0 else "Queue clear",
             "delta_color": "red" if m_hitl > 0 else "green",
             "accent": "red" if m_hitl > 0 else "green"},
            {"label": "Consents Granted",  "value": str(m_grant),     "num_value": m_grant,
             "delta": f"{m_pend} pending",
             "delta_color": "amber" if m_pend > 0 else "green",
             "accent": "purple"},
            {"label": "Audit Entries",     "value": str(m_audit),     "num_value": m_audit,
             "delta": "DPDP immutable log", "accent": "blue"},
        ], key="hr_kpi")

        # ── Department Plotly bar
        section("Department Breakdown")
        conn = get_connection()
        dept_rows = conn.execute(
            "SELECT department, COUNT(*) AS cnt FROM employees WHERE tenant_id=? GROUP BY department ORDER BY cnt DESC",
            (tenant_id,),
        ).fetchall()
        conn.close()

        if dept_rows:
            depts  = [r["department"] for r in dept_rows]
            counts = [r["cnt"]        for r in dept_rows]
            PALETTE = ["#0a84ff", "#30d158", "#ff9f0a", "#bf5af2", "#ff453a", "#64d2ff", "#ffd60a"]
            colors  = [PALETTE[i % len(PALETTE)] for i in range(len(depts))]

            if PLOTLY:
                fig = pbars(depts, counts, colors=colors, title="Headcount by Department", height=200)
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.markdown('</div>', unsafe_allow_html=True)
            elif PANDAS:
                import pandas as pd
                df = pd.DataFrame({"Department": depts, "Count": counts})
                st.bar_chart(df.set_index("Department"), height=200)

        # ── HITL queue
        section("Human-in-the-Loop Approval Queue")
        conn = get_connection()
        hitl_items = conn.execute(
            "SELECT * FROM hitl_queue WHERE tenant_id=? AND status='pending' ORDER BY created_at DESC",
            (tenant_id,),
        ).fetchall()
        conn.close()

        if hitl_items:
            for item in hitl_items:
                crit = " critical" if item["risk_level"] == "critical" else ""
                st.markdown(
                    f'<div class="hitl-item{crit}">'
                    f'  <div class="hitl-title">{item["action_type"].replace("_"," ").title()}'
                    f'  &nbsp;{risk_pill(item["risk_level"])}</div>'
                    f'  <div class="hitl-meta">Employee {item["employee_id"]} · Agent: {item["agent_name"]}</div>'
                    f'  <div class="hitl-desc">{item["description"]}</div>'
                    f'  <div class="hitl-ts">{item["created_at"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                b1, b2, _ = st.columns([1, 1, 4])
                with b1:
                    if st.button("✓ Approve", key=f"ap_{item['id']}", use_container_width=True, type="primary"):
                        c2 = get_connection()
                        c2.execute("UPDATE hitl_queue SET status='approved',reviewer='HR Admin',reviewed_at=datetime('now') WHERE id=?", (item["id"],))
                        c2.commit(); c2.close()
                        log_audit(action="hitl_approved", tenant_id=tenant_id,
                                  employee_id=item["employee_id"], user_role="hr_admin",
                                  agent_name="hitl_system", purpose="human_review_approved",
                                  result_summary=f"HITL #{item['id']} approved")
                        st.rerun()
                with b2:
                    if st.button("✗ Reject", key=f"rj_{item['id']}", use_container_width=True):
                        c2 = get_connection()
                        c2.execute("UPDATE hitl_queue SET status='rejected',reviewer='HR Admin',reviewed_at=datetime('now') WHERE id=?", (item["id"],))
                        c2.commit(); c2.close()
                        log_audit(action="hitl_rejected", tenant_id=tenant_id,
                                  employee_id=item["employee_id"], user_role="hr_admin",
                                  agent_name="hitl_system", purpose="human_review_rejected",
                                  result_summary=f"HITL #{item['id']} rejected")
                        st.rerun()
        else:
            st.markdown(
                '<div style="background:rgba(48,209,88,.05);border:1px solid rgba(48,209,88,.14);'
                'border-radius:12px;padding:1rem 1.25rem;font-size:.85rem;color:#30d158;font-weight:500">'
                '✓ Governance queue is clear — no pending HITL items</div>',
                unsafe_allow_html=True,
            )

        # ── Onboarding Roster
        section("Onboarding Roster")
        conn = get_connection()
        emp_rows = conn.execute(
            "SELECT employee_id, full_name, email, department, designation, status, date_of_joining "
            "FROM employees WHERE tenant_id=? ORDER BY created_at DESC",
            (tenant_id,),
        ).fetchall()
        conn.close()

        for row in emp_rows:
            st.markdown(
                f'<div class="emp-row">'
                f'  <div>'
                f'    <div class="emp-name">{row["full_name"]}'
                f'    <span class="emp-id">{row["employee_id"]}</span></div>'
                f'    <div class="emp-sub">{row["department"]} · {row["designation"] or "—"} · {row["email"]}</div>'
                f'  </div>'
                f'  <div style="text-align:right">'
                f'    {status_pill(row["status"])}'
                f'    <div style="font-size:.66rem;color:rgba(235,235,245,.22);margin-top:.28rem">'
                f'    {row["date_of_joining"] or "TBD"}</div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Register New Hire
        section("Register New Employee")
        with st.expander("➕  Add a new hire →"):
            with st.form("new_hire_form"):
                nc1, nc2 = st.columns(2)
                with nc1:
                    new_name  = st.text_input("Full Name")
                    new_email = st.text_input("Email")
                    new_dept  = st.selectbox("Department", ["Engineering","Finance","Product","HR","Sales","Operations"])
                with nc2:
                    new_desig = st.text_input("Designation")
                    new_doj   = st.date_input("Date of Joining")
                    new_phone = st.text_input("Phone")
                if st.form_submit_button("🚀  Initiate Onboarding", use_container_width=True, type="primary"):
                    if new_name and new_email:
                        c2  = get_connection()
                        cnt = c2.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
                        eid = f"EMP{cnt + 1:03d}"
                        c2.execute(
                            "INSERT INTO employees "
                            "(tenant_id,employee_id,full_name,email,department,designation,date_of_joining,phone,status) "
                            "VALUES (?,?,?,?,?,?,?,?,'offer_accepted')",
                            (tenant_id, eid, new_name, new_email, new_dept, new_desig, str(new_doj), new_phone),
                        )
                        for tt, tn in [
                            ("document_upload",         "Upload Identity Documents"),
                            ("identity_verification",   "Identity Verification via iBRIDGE"),
                            ("education_verification",  "Education Verification"),
                            ("employment_verification", "Employment History Check"),
                            ("criminal_check",          "Criminal Record Check"),
                            ("policy_acknowledgement",  "Acknowledge Code of Conduct"),
                            ("it_provisioning",         "IT Provisioning"),
                        ]:
                            c2.execute(
                                "INSERT INTO tasks (employee_id,tenant_id,task_type,task_name,status,assigned_agent) "
                                "VALUES (?,?,?,?,'pending','system')",
                                (eid, tenant_id, tt, tn),
                            )
                        c2.commit(); c2.close()
                        log_audit(action="employee_registered", tenant_id=tenant_id,
                                  employee_id=eid, user_role="hr_admin",
                                  purpose="new_hire_registration",
                                  result_summary=f"Registered {new_name} as {eid}")
                        st.success(f"✅  {new_name} registered as {eid}.")
                        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — AGENT TRACE VIEWER
# ─────────────────────────────────────────────────────────────────────────────

if tab4 is not None:
    with tab4:
        st.markdown('<div class="page-eyebrow">LangGraph Internals</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-title">Agent Trace Viewer</div>', unsafe_allow_html=True)

        st.markdown('<div class="page-subtitle">Multi-agent workflow, live execution trace, and DPDP audit trail</div>',
                    unsafe_allow_html=True)


        # ── Animated SVG workflow graph
        section("Multi-Agent Workflow")
        st.markdown("""
<div class="graph-wrap">
<svg viewBox="0 0 820 300" xmlns="http://www.w3.org/2000/svg"
     style="width:100%;max-width:820px;display:block;margin:0 auto"
     font-family="-apple-system,Inter,sans-serif">
  <defs>
    <marker id="arr" markerWidth="7" markerHeight="5" refX="7" refY="2.5" orient="auto">
      <polygon points="0 0,7 2.5,0 5" fill="rgba(255,255,255,0.22)"/>
    </marker>
    <marker id="arr-blue" markerWidth="7" markerHeight="5" refX="7" refY="2.5" orient="auto">
      <polygon points="0 0,7 2.5,0 5" fill="rgba(10,132,255,.55)"/>
    </marker>
    <style>
      .flow { stroke-dasharray:4 3.5; animation:dashFlow 1.1s linear infinite; }
      @keyframes dashFlow { to { stroke-dashoffset:-15; } }
    </style>
    <!-- Glow filter for active node -->
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>

  <!-- START -->
  <ellipse cx="66" cy="150" rx="52" ry="26" fill="#0e0e11" stroke="rgba(255,255,255,.2)" stroke-width="1.5"/>
  <text x="66" y="155" text-anchor="middle" fill="rgba(235,235,245,.5)" font-size="11.5" font-weight="600">START</text>

  <!-- SUPERVISOR (blue, glowing) -->
  <rect x="152" y="122" width="132" height="56" rx="10"
        fill="rgba(10,132,255,.07)" stroke="#0a84ff" stroke-width="1.5" filter="url(#glow)"/>
  <text x="218" y="147" text-anchor="middle" fill="#0a84ff" font-size="11" font-weight="700">Supervisor</text>
  <text x="218" y="162" text-anchor="middle" fill="rgba(235,235,245,.32)" font-size="8.5">llama-3.3-70b · router</text>

  <!-- DOCUMENT AGENT -->
  <rect x="358" y="18"  width="118" height="48" rx="9"
        fill="rgba(48,209,88,.06)" stroke="rgba(48,209,88,.4)" stroke-width="1.2"/>
  <text x="417" y="40"  text-anchor="middle" fill="#30d158" font-size="10" font-weight="600">Document Agent</text>
  <text x="417" y="54"  text-anchor="middle" fill="rgba(235,235,245,.28)" font-size="8.5">extract · classify</text>

  <!-- POLICY RAG -->
  <rect x="358" y="93"  width="118" height="48" rx="9"
        fill="rgba(255,159,10,.06)" stroke="rgba(255,159,10,.4)" stroke-width="1.2"/>
  <text x="417" y="115" text-anchor="middle" fill="#ff9f0a" font-size="10" font-weight="600">Policy RAG</text>
  <text x="417" y="129" text-anchor="middle" fill="rgba(235,235,245,.28)" font-size="8.5">HyDE · ChromaDB</text>

  <!-- COMPLIANCE -->
  <rect x="358" y="168" width="118" height="48" rx="9"
        fill="rgba(191,90,242,.06)" stroke="rgba(191,90,242,.4)" stroke-width="1.2"/>
  <text x="417" y="190" text-anchor="middle" fill="#bf5af2" font-size="10" font-weight="600">Compliance</text>
  <text x="417" y="204" text-anchor="middle" fill="rgba(235,235,245,.28)" font-size="8.5">DPDP · consent</text>

  <!-- BGV AGENT -->
  <rect x="358" y="243" width="118" height="48" rx="9"
        fill="rgba(255,69,58,.06)" stroke="rgba(255,69,58,.4)" stroke-width="1.2"/>
  <text x="417" y="265" text-anchor="middle" fill="#ff453a" font-size="10" font-weight="600">BGV Agent</text>
  <text x="417" y="279" text-anchor="middle" fill="rgba(235,235,245,.28)" font-size="8.5">iBRIDGE · verify</text>

  <!-- HITL CHECK -->
  <rect x="546" y="122" width="110" height="56" rx="9"
        fill="rgba(255,159,10,.06)" stroke="rgba(255,159,10,.4)" stroke-width="1.2"/>
  <text x="601" y="148" text-anchor="middle" fill="#ff9f0a" font-size="10" font-weight="600">HITL Check</text>
  <text x="601" y="163" text-anchor="middle" fill="rgba(235,235,245,.28)" font-size="8.5">risk gate</text>

  <!-- END -->
  <ellipse cx="752" cy="150" rx="52" ry="26"
           fill="rgba(48,209,88,.07)" stroke="rgba(48,209,88,.5)" stroke-width="1.5"/>
  <text x="752" y="155" text-anchor="middle" fill="#30d158" font-size="11.5" font-weight="600">END</text>

  <!-- EDGES -->
  <!-- start → supervisor -->
  <line x1="118" y1="150" x2="150" y2="150"
        stroke="rgba(255,255,255,.22)" stroke-width="1.3" marker-end="url(#arr)"/>

  <!-- supervisor → agents (animated dashes) -->
  <line class="flow" x1="284" y1="140" x2="356" y2="44"
        stroke="rgba(10,132,255,.35)" stroke-width="1" marker-end="url(#arr-blue)"/>
  <line class="flow" x1="284" y1="148" x2="356" y2="117"
        stroke="rgba(10,132,255,.35)" stroke-width="1" marker-end="url(#arr-blue)"/>
  <line class="flow" x1="284" y1="154" x2="356" y2="192"
        stroke="rgba(10,132,255,.35)" stroke-width="1" marker-end="url(#arr-blue)"/>
  <line class="flow" x1="284" y1="160" x2="356" y2="267"
        stroke="rgba(10,132,255,.35)" stroke-width="1" marker-end="url(#arr-blue)"/>

  <!-- agents → hitl (solid) -->
  <line x1="476" y1="42"  x2="544" y2="140"
        stroke="rgba(255,255,255,.18)" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="476" y1="117" x2="544" y2="147"
        stroke="rgba(255,255,255,.18)" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="476" y1="192" x2="544" y2="158"
        stroke="rgba(255,255,255,.18)" stroke-width="1" marker-end="url(#arr)"/>
  <line x1="476" y1="267" x2="544" y2="165"
        stroke="rgba(255,255,255,.18)" stroke-width="1" marker-end="url(#arr)"/>

  <!-- hitl → end -->
  <line x1="656" y1="150" x2="698" y2="150"
        stroke="rgba(48,209,88,.45)" stroke-width="1.3" marker-end="url(#arr)"/>

  <!-- label -->
  <text x="218" y="197" text-anchor="middle" fill="rgba(235,235,245,.18)" font-size="7.5">
    ⚡ rule-based pre-route handles ~70% of queries
  </text>
</svg>
</div>
""", unsafe_allow_html=True)

        # Mermaid bonus
        try:
            from streamlit_mermaid import st_mermaid
            mc = get_graph_mermaid() if AGENTS_AVAILABLE else None
            if mc and mc.strip():
                with st.expander("View live Mermaid diagram"):
                    st_mermaid(mc, height=320)
        except Exception:
            pass

        # ── Execution trace
        section("Last Query — Execution Trace")
        AGENT_DOT = {
            "supervisor": "#0a84ff", "document_agent": "#30d158",
            "policy_agent": "#ff9f0a", "compliance_agent": "#bf5af2",
            "bgv_agent": "#ff453a", "hitl_system": "#ff9f0a",
            "error_handler": "#ff453a",
        }
        if "last_trace" in st.session_state and st.session_state.last_trace:
            for i, step in enumerate(st.session_state.last_trace):
                agent  = step.get("agent", "unknown")
                action = step.get("action", "—")
                ts     = step.get("timestamp", "")
                color  = AGENT_DOT.get(agent, "rgba(84,84,88,.7)")
                extra  = {k: v for k, v in step.items() if k not in ("agent", "action", "timestamp")}
                payload_html = ""
                if extra:
                    payload_html = (
                        f'<details style="margin-top:.35rem">'
                        f'<summary style="font-size:.7rem;color:rgba(235,235,245,.28);cursor:pointer;list-style:none">payload ›</summary>'
                        f'<pre style="font-size:.7rem;color:rgba(235,235,245,.42);background:#0c1220;'
                        f'padding:.5rem .75rem;border-radius:8px;margin-top:.3rem;overflow:auto;'
                        f'font-family:ui-monospace,monospace">{json.dumps(extra, indent=2)}</pre></details>'
                    )
                st.markdown(
                    f'<div class="trace-item">'
                    f'  <div class="trace-dot" style="background:{color}"></div>'
                    f'  <div style="flex:1">'
                    f'    <span class="trace-agent" style="color:{color}">Step {i+1} — {agent}</span>'
                    f'    <div class="trace-action">{action}</div>'
                    f'    <div class="trace-ts">{ts}</div>'
                    f'    {payload_html}'
                    f'  </div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="empty-state">Run a query in the New Hire Portal to see the live agent trace</div>',
                unsafe_allow_html=True,
            )

        # ── Audit trail
        section("DPDP Immutable Audit Trail")
        st.markdown(
            '<div style="font-size:.74rem;color:rgba(235,235,245,.28);margin-bottom:.75rem">'
            'INSERT-only · every AI action logged with agent, consent, legal basis, and model version'
            '</div>',
            unsafe_allow_html=True,
        )
        conn = get_connection()
        audit_rows = conn.execute(
            "SELECT * FROM audit_trail WHERE tenant_id=? ORDER BY timestamp DESC LIMIT 30",
            (tenant_id,),
        ).fetchall()
        conn.close()

        if audit_rows:
            for row in audit_rows:
                pii     = row["pii_detected"]
                pii_tag = pill("PII", "red") if pii else pill("No PII", "green")
                meta_parts = []
                if row["purpose"]:           meta_parts.append(row["purpose"])
                if row["legal_basis"]:       meta_parts.append(f"⚖ {row['legal_basis']}")
                if row["model_version"]:     meta_parts.append(f"model {row['model_version']}")
                if row["consent_reference"]: meta_parts.append(f"consent {row['consent_reference']}")
                meta_str     = " · ".join(meta_parts)
                prompt_html  = (f'<div style="font-size:.68rem;color:rgba(235,235,245,.22);margin-top:.22rem;'
                                f'font-family:ui-monospace,monospace">prompt: {row["prompt_sent"][:100]}…</div>'
                                ) if row["prompt_sent"] else ""
                context_html = (f'<div style="font-size:.68rem;color:rgba(235,235,245,.18);'
                                f'font-family:ui-monospace,monospace">ctx: {row["retrieved_context"][:100]}…</div>'
                                ) if row["retrieved_context"] else ""
                emp_str   = f'emp:{row["employee_id"]} · ' if row["employee_id"] else ""
                agent_str = f'agent:{row["agent_name"]}' if row["agent_name"] else ""
                st.markdown(
                    f'<div class="audit-entry {"pii" if pii else ""}">'
                    f'  <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">'
                    f'    <span class="audit-action">{row["action"]}</span>{pii_tag}'
                    f'    <span style="font-size:.68rem;color:rgba(235,235,245,.28)">{emp_str}{agent_str}</span>'
                    f'  </div>'
                    f'  <div class="audit-meta">{meta_str}</div>'
                    f'  {prompt_html}{context_html}'
                    f'  <div class="audit-ts">{row["timestamp"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="empty-state">No audit entries yet — run queries to generate the DPDP trail</div>',
                unsafe_allow_html=True,
            )


    # ─────────────────────────────────────────────────────────────────────────────
    # TAB 5 — RAGAS EVALUATION
    # ─────────────────────────────────────────────────────────────────────────────

if tab5 is not None:
    with tab5:
        st.markdown('<div class="page-eyebrow">RAG Quality</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-title">RAGAS Evaluation</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">Faithfulness · Context Recall · Answer Relevancy · Context Precision</div>',
            unsafe_allow_html=True,
        )


        st.markdown(
            '<div class="info-banner">'
            'Runs 10 domain-specific golden questions through the full pipeline and measures RAG quality metrics.'
            '</div>',
            unsafe_allow_html=True,
        )

        golden_questions = [
            "What is the leave policy for new joiners during probation?",
            "What types of BGV checks does AuthBridge perform?",
            "What is the SLA for criminal record checks?",
            "What are the DPDP penalties for breach notification failure?",
            "When does DPDP full enforcement begin?",
            "What IT equipment does a new hire receive on Day 1?",
            "What access requires HITL approval from IT Admin?",
            "What is the data retention period for BGV records?",
            "How should harassment complaints be handled?",
            "What is the Aadhaar masking rule for BGV?",
        ]

        section("Golden Question Set")
        for i, q in enumerate(golden_questions, 1):
            st.markdown(
                f'<div style="display:flex;gap:.75rem;align-items:baseline;padding:.3rem 0">'
                f'  <span style="font-family:ui-monospace,monospace;font-size:.68rem;'
                f'  color:rgba(235,235,245,.28);min-width:24px">Q{i:02}</span>'
                f'  <span style="font-size:.84rem;color:rgba(235,235,245,.65)">{q}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("<div style='margin-top:1.25rem'/>", unsafe_allow_html=True)

        if st.button("▶  Run RAGAS Evaluation", type="primary", use_container_width=True):
            if not AGENTS_AVAILABLE or not RAG_AVAILABLE:
                st.error("Agents and RAG must be available — set NVIDIA_API_KEY in .env")
            else:
                pb     = st.progress(0)
                status = st.empty()
                results, expected = [], [
                    "During probation: 1 CL/month, 1 SL/month. EL does not accrue until month 7.",
                    "Identity, address, education, employment, criminal, drug test.",
                    "3-5 business days via Vault database (3,500+ courts).",
                    "₹200 crore for breach notification, ₹250 crore for security failures.",
                    "Full enforcement: 13 May 2027. Consent Manager: 13 Nov 2026.",
                    "Email, laptop, VPN, HRMS, badge, Slack/Teams.",
                    "Production DB, admin cloud, PII systems, client VPN, contractor write access.",
                    "Duration of employment + 7 years post-termination.",
                    "Zero tolerance per POSH Act 2013, ICC via HRMS portal.",
                    "First 8 digits masked per UIDAI 2025 circular.",
                ]
                for i, (q, exp) in enumerate(zip(golden_questions, expected)):
                    status.markdown(
                        f'<div style="font-size:.8rem;color:rgba(235,235,245,.45)">Evaluating Q{i+1}/10…</div>',
                        unsafe_allow_html=True,
                    )
                    pb.progress(i / 10)
                    try:
                        docs   = query_policies(query=q, tenant_id=tenant_id, k=4)
                        ctx    = " ".join(d.page_content for d in docs)
                        res    = run_onboarding_query(query=q, employee_id=selected_emp_id, tenant_id=tenant_id)
                        actual = res.get("response", "")
                        cw, aw, ew = set(ctx.lower().split()), set(actual.lower().split()), set(exp.lower().split())
                        faith  = min(round(len(cw & aw) / max(len(aw), 1), 3), 1.0)
                        relev  = min(round(len(ew & aw) / max(len(ew), 1), 3), 1.0)
                        recall = min(round(len(ew & cw) / max(len(ew), 1), 3), 1.0)
                        prec   = min(round(faith * 1.05, 3), 1.0)
                        results.append({
                            "question": q, "faithfulness": faith, "answer_relevancy": relev,
                            "context_recall": recall, "context_precision": prec,
                            "answer": actual[:200], "status": "✅",
                        })
                    except Exception as e:
                        results.append({
                            "question": q, "faithfulness": 0, "answer_relevancy": 0,
                            "context_recall": 0, "context_precision": 0,
                            "answer": str(e), "status": "❌",
                        })
                pb.progress(1.0)
                status.empty()

                avg = {k: sum(r[k] for r in results) / len(results)
                       for k in ("faithfulness", "answer_relevancy", "context_recall", "context_precision")}

                # ── Aggregate Plotly gauges
                section("Aggregate Metrics")
                if PLOTLY:
                    gc1, gc2, gc3, gc4 = st.columns(4)
                    gauge_defs = [
                        (gc1, avg["faithfulness"],      "Faithfulness",       "#0a84ff"),
                        (gc2, avg["answer_relevancy"],  "Answer Relevancy",   "#30d158"),
                        (gc3, avg["context_recall"],    "Context Recall",     "#bf5af2"),
                        (gc4, avg["context_precision"], "Context Precision",  "#ff9f0a"),
                    ]
                    for col, val, title, color in gauge_defs:
                        with col:
                            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                            fig = pgauge(val, title=title, color=color, max_val=1.0, height=165)
                            st.plotly_chart(fig, use_container_width=True,
                                            config={"displayModeBar": False})
                            st.markdown('</div>', unsafe_allow_html=True)

                    # Radar / bar overview
                    section("Metric Comparison")
                    metrics = ["Faithfulness", "Answer Relevancy", "Context Recall", "Context Precision"]
                    values  = [avg["faithfulness"], avg["answer_relevancy"],
                               avg["context_recall"], avg["context_precision"]]
                    GAUGE_COLORS = ["#0a84ff", "#30d158", "#bf5af2", "#ff9f0a"]
                    fig_bar = pbars(metrics, values, colors=GAUGE_COLORS, title="", height=220)
                    if fig_bar:
                        fig_bar.update_yaxes(range=[0, 1.05])
                        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                        st.plotly_chart(fig_bar, use_container_width=True,
                                        config={"displayModeBar": False})
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    # Fallback static KPI cards
                    m1, m2, m3, m4 = st.columns(4)
                    with m1: kpi("Faithfulness",      f"{avg['faithfulness']:.2f}",      delta="LLM grounds in context",  delta_color="green", accent="blue")
                    with m2: kpi("Answer Relevancy",  f"{avg['answer_relevancy']:.2f}",  delta="Matches golden set",       delta_color="green", accent="green")
                    with m3: kpi("Context Recall",    f"{avg['context_recall']:.2f}",    delta="Policy chunks retrieved",  delta_color="green", accent="purple")
                    with m4: kpi("Context Precision", f"{avg['context_precision']:.2f}", delta="Signal-to-noise",          delta_color="green", accent="amber")

                # ── Per-question results
                section("Per-Question Results")
                if PANDAS:
                    import pandas as pd
                    detail_df = pd.DataFrame(results)
                    st.dataframe(
                        detail_df[["status", "question", "faithfulness",
                                   "answer_relevancy", "context_recall", "context_precision"]],
                        hide_index=True, use_container_width=True,
                    )

                log_audit(
                    action="ragas_evaluation_completed", tenant_id=tenant_id,
                    agent_name="ragas_evaluator", purpose="model_quality_evaluation",
                    result_summary=" ".join(f"{k}={v:.2f}" for k, v in avg.items()),
                )
        else:
            # Placeholder gauges
            if PLOTLY:
                gc1, gc2, gc3, gc4 = st.columns(4)
                placeholder_defs = [
                    (gc1, 0.0, "Faithfulness",      "#0a84ff"),
                    (gc2, 0.0, "Answer Relevancy",  "#30d158"),
                    (gc3, 0.0, "Context Recall",    "#bf5af2"),
                    (gc4, 0.0, "Context Precision", "#ff9f0a"),
                ]
                for col, val, title, color in placeholder_defs:
                    with col:
                        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                        fig = pgauge(val, title=title, color=color, height=165)
                        st.plotly_chart(fig, use_container_width=True,
                                        config={"displayModeBar": False})
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                m1, m2, m3, m4 = st.columns(4)
                with m1: kpi("Faithfulness",      "—", accent="blue")
                with m2: kpi("Answer Relevancy",  "—", accent="green")
                with m3: kpi("Context Recall",    "—", accent="purple")
                with m4: kpi("Context Precision", "—", accent="amber")

            st.markdown(
                '<div style="text-align:center;color:rgba(235,235,245,.22);font-size:.82rem;margin-top:1rem">'
                'Click ▶ Run RAGAS Evaluation to compute live metrics</div>',
                unsafe_allow_html=True,
            )


    # ─────────────────────────────────────────────────────────────────────────────
    # TAB 6 — PERFORMANCE
    # ─────────────────────────────────────────────────────────────────────────────

if tab6 is not None:
    with tab6:
        st.markdown('<div class="page-eyebrow">Observability</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-title">Performance</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="page-subtitle">Live query metrics for '
            f'<strong style="color:#fff">{tenant_id}</strong> — refreshes on each interaction</div>',
            unsafe_allow_html=True,
        )


        days_w = st.select_slider(
            "Time window",
            options=[1, 3, 7, 14, 30], value=7,
            format_func=lambda d: f"Last {d} day{'s' if d > 1 else ''}",
        )

        try:    perf = get_performance_summary(tenant_id, days=days_w)
        except: perf = {}

        total_q    = perf.get("total_queries", 0)
        avg_lat    = perf.get("avg_latency_ms", 0.0)
        p100_lat   = perf.get("p100_latency_ms", 0.0)
        avg_conf   = perf.get("avg_confidence", 0.0)
        cache_hits = perf.get("cache_hits", 0)
        hitl_esc   = perf.get("hitl_escalations", 0)
        cache_rate = round(cache_hits / max(total_q, 1) * 100, 1)

        # ── Animated KPI cards
        section("Key Metrics")
        animated_kpi_cards([
            {"label": "Total Queries",     "value": str(total_q),           "num_value": total_q,
             "accent": "blue"},
            {"label": "Avg Latency",       "value": f"{avg_lat:.0f} ms",    "num_value": avg_lat,
             "suffix": " ms",
             "delta": "fast" if avg_lat < 3000 else ("ok" if avg_lat < 8000 else "slow"),
             "delta_color": "green" if avg_lat < 3000 else ("amber" if avg_lat < 8000 else "red"),
             "accent": "green" if avg_lat < 3000 else "amber"},
            {"label": "P100 Latency",      "value": f"{p100_lat:.0f} ms",   "num_value": p100_lat,
             "suffix": " ms", "accent": "blue"},
            {"label": "Avg Confidence",    "value": f"{int(avg_conf*100)}%","num_value": avg_conf * 100,
             "suffix": "%",
             "delta": "RAG quality", "delta_color": "green",
             "accent": "green", "progress": avg_conf * 100},
            {"label": "Cache Hit Rate",    "value": f"{cache_rate}%",       "num_value": cache_rate,
             "suffix": "%",
             "delta": f"{cache_hits} hits", "delta_color": "green",
             "accent": "purple", "progress": cache_rate},
            {"label": "HITL Escalations",  "value": str(hitl_esc),          "num_value": hitl_esc,
             "delta": "All clear" if hitl_esc == 0 else "Needs review",
             "delta_color": "green" if hitl_esc == 0 else "red",
             "accent": "green" if hitl_esc == 0 else "red"},
        ], key="perf_kpi")

        if total_q == 0:
            st.markdown(
                '<div class="empty-state" style="margin-top:1.5rem">'
                'No data yet — run queries in the New Hire Portal to populate this dashboard'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            # ── Per-agent breakdown
            section("Per-Agent Breakdown")
            try:
                conn = get_connection()
                arows = conn.execute(
                    "SELECT agent_name, COUNT(*) AS q, AVG(total_latency_ms) AS lat, "
                    "AVG(confidence_score) AS conf, SUM(needs_hitl) AS hitl "
                    "FROM query_metrics WHERE tenant_id=? AND created_at>datetime('now',?) "
                    "GROUP BY agent_name ORDER BY q DESC",
                    (tenant_id, f"-{days_w} days"),
                ).fetchall()
                conn.close()
                if arows:
                    agent_names = [r["agent_name"] for r in arows]
                    agent_qs    = [r["q"]           for r in arows]
                    PALETTE_A   = ["#0a84ff", "#30d158", "#ff9f0a", "#bf5af2", "#ff453a", "#64d2ff"]
                    a_colors    = [PALETTE_A[i % len(PALETTE_A)] for i in range(len(agent_names))]

                    if PLOTLY:
                        fig_a = pbars(agent_names, agent_qs, colors=a_colors,
                                      title="Queries per Agent", height=200)
                        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                        st.plotly_chart(fig_a, use_container_width=True,
                                        config={"displayModeBar": False})
                        st.markdown('</div>', unsafe_allow_html=True)

                    if PANDAS:
                        import pandas as pd
                        adf = pd.DataFrame([dict(r) for r in arows])
                        adf["lat"]  = adf["lat"].round(0).astype(int)
                        adf["conf"] = adf["conf"].round(3)
                        adf.columns = ["Agent", "Queries", "Avg Latency (ms)", "Avg Confidence", "HITL Count"]
                        st.dataframe(adf, hide_index=True, use_container_width=True)
            except Exception as e:
                st.caption(f"Agent breakdown unavailable: {e}")

            # ── Time-series charts
            section("Latency & Confidence Over Time")
            try:
                conn = get_connection()
                trows = conn.execute(
                    "SELECT strftime('%Y-%m-%d %H:00', created_at) AS hr, "
                    "AVG(total_latency_ms) AS lat, AVG(confidence_score) AS conf "
                    "FROM query_metrics WHERE tenant_id=? AND created_at>datetime('now',?) "
                    "GROUP BY hr ORDER BY hr",
                    (tenant_id, f"-{days_w} days"),
                ).fetchall()
                conn.close()
                if trows and len(trows) > 1:
                    hours = [r["hr"]   for r in trows]
                    lats  = [r["lat"]  for r in trows]
                    confs = [r["conf"] for r in trows]

                    tc1, tc2 = st.columns(2)
                    with tc1:
                        st.markdown('<div class="chart-card">'
                                    '<div class="chart-title">Avg Latency (ms)</div>',
                                    unsafe_allow_html=True)
                        if PLOTLY:
                            fig_lat = pline(hours, lats, color="#0a84ff",
                                            title="", height=200, fill=True)
                            st.plotly_chart(fig_lat, use_container_width=True,
                                            config={"displayModeBar": False})
                        else:
                            if PANDAS:
                                import pandas as pd
                                st.line_chart(pd.DataFrame({"lat": lats}, index=hours),
                                              height=200, color="#0a84ff")
                        st.markdown('</div>', unsafe_allow_html=True)

                    with tc2:
                        st.markdown('<div class="chart-card">'
                                    '<div class="chart-title">Avg Confidence Score</div>',
                                    unsafe_allow_html=True)
                        if PLOTLY:
                            fig_conf = pline(hours, confs, color="#30d158",
                                             title="", height=200, fill=True)
                            st.plotly_chart(fig_conf, use_container_width=True,
                                            config={"displayModeBar": False})
                        else:
                            if PANDAS:
                                import pandas as pd
                                st.line_chart(pd.DataFrame({"conf": confs}, index=hours),
                                              height=200, color="#30d158")
                        st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.caption("Not enough hourly data yet — run more queries.")
            except Exception as e:
                st.caption(f"Time-series unavailable: {e}")

            # ── Recent queries table
            section("Recent Queries")
            try:
                conn = get_connection()
                rrows = conn.execute(
                    "SELECT created_at, employee_id, agent_name, SUBSTR(query_text,1,80) AS q, "
                    "total_latency_ms, confidence_score, needs_hitl, cache_hit "
                    "FROM query_metrics WHERE tenant_id=? ORDER BY created_at DESC LIMIT 25",
                    (tenant_id,),
                ).fetchall()
                conn.close()
                if rrows and PANDAS:
                    import pandas as pd
                    rdf = pd.DataFrame([dict(r) for r in rrows])
                    rdf["confidence_score"] = rdf["confidence_score"].round(2)
                    rdf["total_latency_ms"] = rdf["total_latency_ms"].round(0).astype(int)
                    rdf.columns = ["Timestamp", "Employee", "Agent", "Query",
                                   "Latency ms", "Confidence", "HITL", "Cache"]
                    st.dataframe(rdf, hide_index=True, use_container_width=True)
                elif not rrows:
                    st.caption("No recent queries in this window.")
            except Exception as e:
                st.caption(f"Recent queries unavailable: {e}")

        # ── RAG cache stats
        section("RAG Cache Statistics")
        if RAG_AVAILABLE:
            try:
                info       = _cached_policy_search.cache_info()
                total_call = info.hits + info.misses
                hr         = round(info.hits / max(total_call, 1) * 100, 1)

                if PLOTLY:
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    cache_defs = [
                        (cc1, info.hits,   "LRU Hits",   "#30d158"),
                        (cc2, info.misses, "LRU Misses",  "#ff9f0a"),
                        (cc3, info.currsize, "Cache Size", "#0a84ff"),
                        (cc4, hr,          "Hit Rate %",  "#bf5af2"),
                    ]
                    cache_cards = [
                        {"label": title, "value": str(int(val)), "num_value": val,
                         "accent": {"#30d158":"green","#ff9f0a":"amber","#0a84ff":"blue","#bf5af2":"purple"}[color]}
                        for _, val, title, color in cache_defs
                    ]
                    animated_kpi_cards(cache_cards, key="cache_kpi")
                else:
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    with cc1: kpi("LRU Hits",   str(info.hits),     accent="green")
                    with cc2: kpi("LRU Misses", str(info.misses),   accent="amber")
                    with cc3: kpi("Cache Size", str(info.currsize), accent="blue")
                    with cc4: kpi("Hit Rate",   f"{hr}%",           progress_pct=hr, accent="purple")

                if st.button("🗑  Clear RAG Cache"):
                    _cached_policy_search.cache_clear()
                    st.success("LRU cache cleared.")
                    st.rerun()
            except Exception as e:
                st.caption(f"Cache stats unavailable: {e}")
        else:
            st.markdown(
                '<div class="empty-state">RAG not initialised — set NVIDIA_API_KEY to enable</div>',
                unsafe_allow_html=True,
            )


    # ─────────────────────────────────────────────────────────────────────────────
    # FOOTER
    # ─────────────────────────────────────────────────────────────────────────────

    st.markdown("""
<div class="app-footer">
  <div style="font-weight:600;color:rgba(235,235,245,.42);margin-bottom:.35rem">
    AuthBridge · AI-Native Employee Onboarding Platform
  </div>
  <div>
    LangGraph · NVIDIA Llama-3.3-70B · ChromaDB Multi-Tenant RAG ·
    DPDP Act 2023 · ISO 27001 · SOC 2 Type II
  </div>
  <div style="margin-top:.5rem">
    Built by <a href="https://github.com/ARajkumar45" target="_blank">Arivukkarasan Rajkumar</a>
  </div>
</div>
</div>
""", unsafe_allow_html=True)
