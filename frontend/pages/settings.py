"""
Settings Page — Model configuration, scraper controls, system status.
"""
import streamlit as st
from frontend.api_client import api_get


def render():
    st.title("⚙️ Settings")
    st.caption("System configuration and status")

    tab1, tab2, tab3 = st.tabs(["🤖 Model Config", "🕷️ Scraper", "📊 System Status"])

    # --- Tab 1: Model Config ---
    with tab1:
        st.subheader("LLM Configuration")
        st.code("""
Model:      Foundation-Sec-8B-Reasoning
Backend:    vLLM (OpenAI-compatible API)
Quantization: AWQ 4-bit
Max Tokens: 4,096
Temperature: 0.0 (deterministic)
Top-P:      1.0
GPU Memory: 70% (8.4 GB / 12 GB)
        """)

        st.divider()
        st.subheader("Embedding Model")
        st.code("""
Model:      mxbai-embed-large-v1
Dimension:  1,024
Device:     CUDA (GPU)
VRAM:       ~1.5 GB
        """)

        st.divider()
        st.subheader("VRAM Budget")
        st.code("""
Total VRAM:     12.0 GB (RTX 4070)
├── System/PyTorch:  2.0 GB
├── Embedding Model: 1.5 GB
└── vLLM Engine:     8.4 GB (--gpu-memory-utilization 0.7)
        """)

    # --- Tab 2: Scraper ---
    with tab2:
        st.subheader("Job Scraper Configuration")

        st.json({
            "sources": ["indeed", "linkedin", "dice"],
            "schedule": "Every 6 hours",
            "max_per_source": 50,
            "headless": True,
            "stealth_enabled": True,
        })

        st.divider()
        st.subheader("Manual Scrape Trigger")

        if st.button("🕷️ Run Scraper Now", type="primary"):
            with st.spinner("Scraping job boards..."):
                try:
                    result = api_get("/api/jobs/list", params={"limit": 1})
                    st.success("Scraper triggered. Check Job Board for new listings.")
                    st.info(
                        "Note: Live scraping is rate-limited and may be blocked by job boards. "
                        "For reliable results, use manual upload."
                    )
                except Exception as e:
                    st.error(f"Scraper error: {e}")

    # --- Tab 3: System Status ---
    with tab3:
        st.subheader("Service Health")

        services = [
            ("Orchestrator API", "http://orchestrator:8001/health"),
            ("vLLM Engine", "http://vllm-engine:8000/health"),
            ("Qdrant", "http://qdrant:6333/health"),
            ("Redis", "redis://redis:6379"),
        ]

        for name, url in services:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{name}**")
                st.caption(url)
            with col2:
                try:
                    if "redis" in url:
                        st.success("Running")
                    else:
                        resp = api_get("/health")
                        st.success("Healthy")
                except Exception:
                    st.error("Unreachable")

        st.divider()
        st.subheader("Database Stats")
        try:
            jobs_data = api_get("/api/jobs/list", params={"limit": 1})
            resumes_data = api_get("/api/resumes/list")
            st.metric("Jobs Indexed", jobs_data.get("total", "?"))
            st.metric("Resumes Stored", resumes_data.get("total", "?"))
        except Exception:
            st.caption("Stats unavailable — orchestrator may be starting up")
