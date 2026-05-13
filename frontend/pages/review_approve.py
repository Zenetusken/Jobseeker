"""
Review & Approve Page — Side-by-side diff review and one-click submission.
"""
import streamlit as st
from frontend.api_client import api_post
from frontend.components.diff_view import render_bullet_diff, render_section_diff


def render():
    st.title("📝 Review & Approve")
    st.caption("Review the LLM-tailored resume before submission")

    rewrite_result = st.session_state.get("rewrite_result")

    if not rewrite_result:
        st.info("No tailored resume to review. Go to 'Staged Applications' and click 'Tailor Resume' on a matched job.")
        if st.button("🎯 Go to Staged Applications"):
            st.switch_page("frontend/pages/staged_apps.py")
        return

    # Header
    st.subheader(f"🎯 {rewrite_result.get('job_title', 'Unknown Position')}")
    st.caption(f"🏢 {rewrite_result.get('company', 'Unknown Company')}")
    st.metric("Match Score", f"{rewrite_result.get('match_score', 0):.1%}")

    st.divider()

    # Overall rationale
    tailored = rewrite_result.get("tailored_resume", {})
    rationale = tailored.get("overall_rationale", "")
    if rationale:
        with st.expander("📋 Overall Rationale", expanded=True):
            st.info(rationale)

    # Summary diff
    original_summary = rewrite_result.get("original_resume", {}).get("summary", "")
    tailored_summary = tailored.get("tailored_summary", "")
    if tailored_summary:
        st.subheader("📝 Summary Changes")
        render_section_diff("Professional Summary", original_summary, tailored_summary)

    # Skills
    skills = tailored.get("skills_highlighted", [])
    if skills:
        st.subheader("🔧 Highlighted Skills")
        st.markdown(" | ".join([f"`{s}`" for s in skills]))

    # Certifications
    certs = tailored.get("certifications_emphasized", [])
    if certs:
        st.subheader("🎓 Emphasized Certifications")
        st.markdown(" | ".join([f"`{c}`" for c in certs]))

    # Experience bullets — the core diff
    st.divider()
    st.subheader("💼 Experience Bullet Changes")

    diffs = rewrite_result.get("diff", [])
    bullet_diffs = [d for d in diffs if d.get("section", "").startswith("experience:")]
    other_diffs = [d for d in diffs if not d.get("section", "").startswith("experience:")]

    # Group bullets by experience entry
    current_section = None
    bullets_for_section = []

    for d in bullet_diffs:
        section = d.get("section", "")
        if section != current_section:
            if bullets_for_section:
                st.markdown(f"**{current_section}**")
                render_bullet_diff(bullets_for_section)
                st.divider()
            current_section = section
            bullets_for_section = [d]
        else:
            bullets_for_section.append(d)

    if bullets_for_section:
        st.markdown(f"**{current_section}**")
        render_bullet_diff(bullets_for_section)

    # Other diffs
    for d in other_diffs:
        section = d.get("section", "")
        render_section_diff(
            section,
            str(d.get("original", "")),
            str(d.get("tailored", "")),
        )

    # --- Action Buttons ---
    st.divider()
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("🔄 Re-generate", use_container_width=True):
            st.session_state.pop("rewrite_result", None)
            st.rerun()

    with col2:
        if st.button("❌ Discard", use_container_width=True):
            st.session_state.pop("rewrite_result", None)
            st.success("Discarded. Go back to Staged Applications.")
            st.rerun()

    with col3:
        job_url = st.text_input(
            "Application URL",
            placeholder="https://careers.example.com/apply/123",
            key="job_url_input",
        )

    st.divider()

    # The big submit button
    if st.button("✅ Approve & Submit Application", type="primary", use_container_width=True):
        if not job_url:
            st.error("Please provide the application URL above.")
        else:
            with st.spinner("🚀 Dispatching application to Playwright automation..."):
                try:
                    submit_result = api_post("/api/submit/apply", {
                        "job_id": st.session_state.get("rewrite_job_id", ""),
                        "resume_id": "from_session",
                        "tailored_resume": tailored,
                        "job_url": job_url,
                    })
                    task_id = submit_result.get("task_id", "")
                    st.success(f"✅ Application dispatched! Task ID: {task_id}")
                    st.info("The application is being submitted in the background. Check 'Application History' for status.")

                    # Clear state
                    st.session_state.pop("rewrite_result", None)
                    st.session_state.pop("rewrite_job_id", None)

                except Exception as e:
                    st.error(f"Submission failed: {e}")
