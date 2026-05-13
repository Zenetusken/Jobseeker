"""
Job Board Page — Browse scraped jobs, upload new ones, trigger matching.
"""
import streamlit as st
from frontend.api_client import api_get, api_post, api_upload


def render():
    st.title("📋 Job Board")
    st.caption("Browse scraped cybersecurity jobs or upload your own")

    tab1, tab2 = st.tabs(["🔍 Browse Jobs", "📤 Upload Job"])

    # --- Tab 1: Browse ---
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            source_filter = st.selectbox(
                "Source", ["all", "indeed", "linkedin", "dice", "manual", "file_upload"]
            )
        with col2:
            limit = st.slider("Jobs per page", 10, 100, 50)
        with col3:
            if st.button("🔄 Refresh Jobs", use_container_width=True):
                st.rerun()

        params = {"limit": limit}
        if source_filter != "all":
            params["source"] = source_filter

        try:
            data = api_get("/api/jobs/list", params=params)
            jobs = data.get("jobs", [])

            if not jobs:
                st.info("No jobs found. Upload some or wait for the scraper to run.")
            else:
                st.caption(f"Showing {len(jobs)} jobs")

                for job in jobs:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.subheader(job.get("title", "Untitled"))
                            st.caption(
                                f"🏢 {job.get('company', 'Unknown')} | "
                                f"📍 {job.get('location', 'Remote')} | "
                                f"📡 {job.get('source', 'unknown')}"
                            )
                            certs = job.get("required_certs", [])
                            skills = job.get("required_skills", [])
                            if certs:
                                st.caption(f"🎓 Certs: {', '.join(certs[:5])}")
                            if skills:
                                st.caption(f"🔧 Skills: {', '.join(skills[:8])}")
                        with c2:
                            if st.button("🎯 Match", key=f"match_{job['id']}", use_container_width=True):
                                st.session_state["selected_job_id"] = job["id"]
                                st.switch_page("frontend/pages/staged_apps.py")
        except Exception as e:
            st.error(f"Failed to load jobs: {e}")

    # --- Tab 2: Upload ---
    with tab2:
        st.subheader("Upload a Job Description")

        upload_method = st.radio("Method", ["Paste Text", "Upload File", "Batch JSON"])

        if upload_method == "Paste Text":
            with st.form("paste_job"):
                title = st.text_input("Job Title")
                company = st.text_input("Company")
                location = st.text_input("Location", "Remote")
                description = st.text_area("Job Description", height=200)
                url = st.text_input("Application URL (optional)")
                submitted = st.form_submit_button("Ingest Job")

                if submitted and title and description:
                    try:
                        result = api_post("/api/jobs/ingest", {
                            "title": title,
                            "company": company,
                            "location": location,
                            "description": description,
                            "url": url,
                            "source": "manual",
                        })
                        st.success(f"Job ingested: {result.get('job_id')}")
                    except Exception as e:
                        st.error(f"Failed: {e}")

        elif upload_method == "Upload File":
            uploaded = st.file_uploader("Choose a text file", type=["txt", "md"])
            if uploaded:
                try:
                    result = api_upload(
                        "/api/jobs/ingest/file",
                        uploaded.read(),
                        uploaded.name,
                    )
                    st.success(f"Ingested: {result.get('job_id')}")
                except Exception as e:
                    st.error(f"Failed: {e}")

        elif upload_method == "Batch JSON":
            st.caption("Paste a JSON array of job objects:")
            st.code("""
[
  {
    "title": "Security Engineer",
    "company": "Acme Corp",
    "location": "Remote",
    "description": "Looking for a security engineer with SIEM experience...",
    "url": "",
    "source": "batch"
  }
]
            """)
            batch_json = st.text_area("JSON", height=200)
            if st.button("Ingest Batch"):
                import json
                try:
                    jobs = json.loads(batch_json)
                    result = api_post("/api/jobs/ingest/batch", {"jobs": jobs})
                    st.success(f"Ingested {result.get('count')} jobs")
                except Exception as e:
                    st.error(f"Failed: {e}")
