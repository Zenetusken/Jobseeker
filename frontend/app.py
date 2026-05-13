"""
Jobseeker Dashboard — Streamlit Frontend
Multi-page app for job browsing, resume management, match review, and submission.
"""
import streamlit as st

st.set_page_config(
    page_title="Jobseeker AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Sidebar Navigation
# ============================================================
st.sidebar.title("🎯 Jobseeker AI")
st.sidebar.caption("Cybersecurity Resume Automation")

page = st.sidebar.radio(
    "Navigate",
    [
        "📋 Job Board",
        "📄 My Resumes",
        "🎯 Staged Applications",
        "📝 Review & Approve",
        "📊 Application History",
        "⚙️ Settings",
    ],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption("vLLM: Foundation-Sec-8B (AWQ)")
st.sidebar.caption("Qdrant Vector DB")
st.sidebar.caption("RTX 4070 | 12GB VRAM")

# ============================================================
# Page Routing
# ============================================================
if page == "📋 Job Board":
    from frontend.pages.job_board import render
    render()
elif page == "📄 My Resumes":
    from frontend.pages.my_resumes import render
    render()
elif page == "🎯 Staged Applications":
    from frontend.pages.staged_apps import render
    render()
elif page == "📝 Review & Approve":
    from frontend.pages.review_approve import render
    render()
elif page == "📊 Application History":
    from frontend.pages.application_history import render
    render()
elif page == "⚙️ Settings":
    from frontend.pages.settings import render
    render()
