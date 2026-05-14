"""
Application History Page — Track submitted applications and their status.
"""
import streamlit as st
from frontend.api_client import api_get

STATUS_COLORS = {
    "queued": "🟡",
    "started": "🔵",
    "success": "🟢",
    "submitted": "🟢",
    "failed": "🔴",
    "retry": "🟠",
}


def render():
    st.title("📊 Application History")
    st.caption("Track your submitted applications")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    try:
        data = api_get("/api/submit/history", params={"limit": 50})
        submissions = data.get("submissions", [])
    except Exception as e:
        st.error(f"Could not load history: {e}")
        submissions = []

    if not submissions:
        st.info(
            "No submissions yet. Go to **Staged Applications** → Tailor → "
            "**Review & Approve** → submit your first application."
        )
    else:
        st.caption(f"Showing {len(submissions)} submission(s)")

        with st.container(border=True):
            header_cols = st.columns([3, 2, 1, 2])
            header_cols[0].markdown("**Job Title**")
            header_cols[1].markdown("**Company**")
            header_cols[2].markdown("**Status**")
            header_cols[3].markdown("**Submitted At**")
            st.divider()

            for sub in submissions:
                status = sub.get("status", "queued").lower()
                icon = STATUS_COLORS.get(status, "⚪")
                cols = st.columns([3, 2, 1, 2])
                cols[0].markdown(sub.get("job_title", "Unknown Position"))
                cols[1].markdown(sub.get("company", "Unknown"))
                cols[2].markdown(f"{icon} {status}")
                submitted_at = sub.get("submitted_at", "")
                if submitted_at:
                    submitted_at = submitted_at.replace("T", " ")[:16]
                cols[3].markdown(submitted_at or "—")

                error = sub.get("error")
                if error:
                    with st.expander(f"❌ Error — {sub.get('job_title', '')}"):
                        st.code(error)

    st.divider()

    # Task status deep-dive
    st.subheader("Check Task Status")
    task_id = st.text_input("Celery Task ID", placeholder="e.g., abc123-def456")
    if task_id and st.button("Check Status"):
        try:
            result = api_get(f"/api/submit/status/{task_id}")
            st.json(result)
        except Exception as e:
            st.error(f"Failed to check status: {e}")
