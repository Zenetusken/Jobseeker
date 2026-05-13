"""
My Resumes Page — Upload and manage candidate resumes.
"""
import streamlit as st
import json
from frontend.api_client import api_get, api_post, api_upload


def render():
    st.title("📄 My Resumes")
    st.caption("Upload and manage your base resumes")

    tab1, tab2, tab3 = st.tabs(["📤 Upload Resume", "📋 Stored Resumes", "✏️ JSON Editor"])

    # --- Tab 1: Upload ---
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Upload File")
            label = st.text_input("Resume Label", "default", key="file_label")
            uploaded = st.file_uploader(
                "Choose resume file",
                type=["pdf", "docx", "txt", "md"],
                key="resume_uploader",
            )
            if uploaded:
                with st.spinner("Parsing resume..."):
                    try:
                        result = api_upload(
                            "/api/resumes/upload",
                            uploaded.read(),
                            uploaded.name,
                            params={"label": label},
                        )
                        st.success(f"Resume parsed! ID: {result.get('resume_id')}")
                        st.json({
                            "certs_found": result.get("certs_found", []),
                            "skills_found": result.get("skills_found", []),
                        })
                    except Exception as e:
                        st.error(f"Parse failed: {e}")

        with col2:
            st.subheader("Upload JSON")
            st.caption("Paste a structured JSON resume:")
            st.code("""
{
  "contact_info": {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "555-0123",
    "location": "Washington, DC"
  },
  "summary": "Cybersecurity engineer with 5 years...",
  "experience": [
    {
      "title": "Security Analyst",
      "company": "Tech Corp",
      "start_date": "2020",
      "end_date": "Present",
      "bullets": [
        "Managed SIEM deployment across 500+ endpoints",
        "Led incident response for 50+ security events"
      ]
    }
  ],
  "education": [
    {"degree": "BS Computer Science", "school": "MIT"}
  ],
  "certifications": [
    {"name": "CISSP"}, {"name": "CEH"}
  ],
  "skills": ["SIEM", "Splunk", "Incident Response", "Python"]
}
            """)
            json_label = st.text_input("Label", "json_resume", key="json_label")
            json_text = st.text_area("Resume JSON", height=300, key="json_input")

            if st.button("Upload JSON Resume"):
                try:
                    resume_data = json.loads(json_text)
                    result = api_post("/api/resumes/upload/json", {
                        "resume": resume_data,
                        "label": json_label,
                    })
                    st.success(f"Resume stored! ID: {result.get('resume_id')}")
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {e}")
                except Exception as e:
                    st.error(f"Failed: {e}")

    # --- Tab 2: Stored Resumes ---
    with tab2:
        try:
            data = api_get("/api/resumes/list")
            resumes = data.get("resumes", [])

            if not resumes:
                st.info("No resumes stored yet. Upload one above.")
            else:
                for resume in resumes:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.subheader(resume.get("label", "Unnamed"))
                            st.caption(f"📄 {resume.get('filename', 'unknown')}")
                            certs = resume.get("certs", [])
                            skills = resume.get("skills", [])
                            if certs:
                                st.caption(f"🎓 {', '.join(certs)}")
                            if skills:
                                st.caption(f"🔧 {', '.join(skills[:10])}")
                        with c2:
                            st.caption(f"ID: {resume['id'][:8]}...")
                            if st.button("🗑️ Delete", key=f"del_{resume['id']}"):
                                try:
                                    api_get(f"/api/resumes/{resume['id']}")
                                    st.rerun()
                                except Exception:
                                    st.rerun()
        except Exception as e:
            st.error(f"Failed to load resumes: {e}")

    # --- Tab 3: JSON Editor ---
    with tab3:
        st.subheader("Build Resume from Scratch")
        st.caption("Fill in the form to create a structured resume")

        with st.form("build_resume"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            location = st.text_input("Location")
            summary = st.text_area("Professional Summary", height=80)

            st.divider()
            st.caption("Experience (one entry)")
            exp_title = st.text_input("Job Title")
            exp_company = st.text_input("Company")
            exp_bullets = st.text_area("Bullet Points (one per line)", height=100)

            st.divider()
            st.caption("Skills & Certs")
            skills_str = st.text_input("Skills (comma-separated)", "SIEM, Splunk, Python")
            certs_str = st.text_input("Certifications (comma-separated)", "CISSP, CEH")

            submitted = st.form_submit_button("Build & Upload Resume")

            if submitted and name:
                resume = {
                    "contact_info": {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "location": location,
                    },
                    "summary": summary,
                    "experience": [{
                        "title": exp_title,
                        "company": exp_company,
                        "bullets": [b.strip() for b in exp_bullets.split("\n") if b.strip()],
                    }],
                    "skills": [s.strip() for s in skills_str.split(",") if s.strip()],
                    "certifications": [{"name": c.strip()} for c in certs_str.split(",") if c.strip()],
                }

                try:
                    result = api_post("/api/resumes/upload/json", {
                        "resume": resume,
                        "label": f"{name}'s Resume",
                    })
                    st.success(f"Resume created! ID: {result.get('resume_id')}")
                except Exception as e:
                    st.error(f"Failed: {e}")
