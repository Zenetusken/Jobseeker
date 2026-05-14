"""
Staged Applications Page — View matched jobs and trigger LLM rewrite.
"""
import streamlit as st
from frontend.api_client import api_get, api_post


def render():
    st.title("🎯 Staged Applications")
    st.caption("Jobs matched to your resume — ready for tailoring")

    # Select resume
    try:
        resumes_data = api_get("/api/resumes/list")
        resumes = resumes_data.get("resumes", [])
    except Exception:
        resumes = []

    if not resumes:
        st.warning("No resumes found. Upload one in 'My Resumes' first.")
        return

    resume_options = {r["label"]: r["id"] for r in resumes}
    selected_label = st.selectbox("Select Resume", list(resume_options.keys()))
    resume_id = resume_options[selected_label]

    col1, col2, col3 = st.columns(3)
    with col1:
        top_k = st.slider("Max matches", 5, 30, 10)
    with col2:
        min_score = st.slider("Min score", 0.0, 1.0, 0.3, 0.05)
    with col3:
        if st.button("🔍 Run Matching", use_container_width=True, type="primary"):
            st.session_state["match_triggered"] = True

    if st.session_state.get("match_triggered"):
        with st.spinner("Running vector search + hard filters..."):
            try:
                match_data = api_post("/api/match/jobs", {
                    "resume_id": resume_id,
                    "top_k": top_k,
                    "min_score": min_score,
                })
                matches = match_data.get("matches", [])

                if not matches:
                    st.info("No matching jobs found. Try lowering the min score or uploading more jobs.")
                else:
                    st.success(f"Found {len(matches)} matches")
                    st.session_state["current_matches"] = matches
            except Exception as e:
                st.error(f"Matching failed: {e}")

    matches = st.session_state.get("current_matches", [])
    if matches:
        for i, match in enumerate(matches):
            passes = match.get("hard_filter_pass", True)
            border_color = "green" if passes else "orange"

            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    status_icon = "✅" if passes else "⚠️"
                    st.subheader(f"{status_icon} {match.get('title', 'Untitled')}")
                    st.caption(
                        f"🏢 {match.get('company', 'Unknown')} | "
                        f"📍 {match.get('location', 'Remote')}"
                    )
                    score = match.get("score", 0)
                    st.progress(min(score, 1.0), text=f"Match: {score:.1%}")

                    if not passes:
                        missing = match.get("missing_certs", [])
                        if missing:
                            st.caption(f"❌ Missing certs: {', '.join(missing)}")
                with c2:
                    certs = match.get("required_certs", [])
                    if certs:
                        st.caption("🎓 Required:")
                        for c in certs[:5]:
                            st.caption(f"  • {c}")
                with c3:
                    if st.button("✏️ Tailor Resume", key=f"tailor_{i}", use_container_width=True, type="primary"):
                        with st.spinner("🤖 Foundation-Sec-8B is rewriting your resume..."):
                            try:
                                rewrite_data = api_post("/api/rewrite/tailor", {
                                    "resume_id": resume_id,
                                    "job_id": match["job_id"],
                                    "match_score": match.get("score", 0.0),
                                })
                                st.session_state["rewrite_result"] = rewrite_data
                                st.session_state["rewrite_job_id"] = match["job_id"]
                                st.session_state["rewrite_job_title"] = match.get("title", "")
                                st.session_state["rewrite_company"] = match.get("company", "")
                                st.session_state["current_resume_id"] = resume_id
                                st.rerun()
                            except Exception as e:
                                st.error(f"Rewrite failed: {e}")

    # If a rewrite was just completed, show a link to review
    if st.session_state.get("rewrite_result"):
        st.divider()
        st.success("✅ Resume tailored! Go to 'Review & Approve' to see the changes.")
        if st.button("📝 Go to Review & Approve", use_container_width=True, type="primary"):
            st.switch_page("frontend/pages/review_approve.py")
