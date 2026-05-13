"""
Application History Page — Track submitted applications and their status.
"""
import streamlit as st
from frontend.api_client import api_get


def render():
    st.title("📊 Application History")
    st.caption("Track your submitted applications")

    # In production, this would query a persistent database.
    # For MVP, we show a placeholder with the architecture explanation.

    st.info(
        "Application history is tracked via Celery task results in Redis. "
        "Each submission creates a task with status: queued → processing → submitted/failed."
    )

    # Simulated history for demo
    with st.container(border=True):
        st.subheader("Recent Submissions")
        st.caption("Submissions will appear here after you approve and submit applications.")

        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        with col1:
            st.markdown("**Job Title**")
        with col2:
            st.markdown("**Company**")
        with col3:
            st.markdown("**Status**")
        with col4:
            st.markdown("**Date**")

        st.divider()
        st.caption("No submissions yet. Go to 'Review & Approve' to submit your first application.")

    st.divider()

    # Task status checker
    st.subheader("Check Task Status")
    task_id = st.text_input("Celery Task ID", placeholder="e.g., abc123-def456")
    if task_id and st.button("Check Status"):
        try:
            result = api_get(f"/api/submit/status/{task_id}")
            st.json(result)
        except Exception as e:
            st.error(f"Failed to check status: {e}")
