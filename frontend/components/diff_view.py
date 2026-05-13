"""
Diff View Component — Side-by-side comparison of original vs tailored resume bullets.
"""
import streamlit as st
import difflib


def render_diff(original_text: str, tailored_text: str):
    """Render a side-by-side diff with color-coded additions/removals."""
    diff = list(difflib.ndiff(
        original_text.splitlines(keepends=True),
        tailored_text.splitlines(keepends=True),
    ))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Original**")
    with col2:
        st.markdown("**Tailored**")

    for line in diff:
        if line.startswith("- "):
            with col1:
                st.markdown(
                    f"<span style='background-color:#ffcccc;padding:2px 4px;border-radius:3px;'>{line[2:]}</span>",
                    unsafe_allow_html=True,
                )
        elif line.startswith("+ "):
            with col2:
                st.markdown(
                    f"<span style='background-color:#ccffcc;padding:2px 4px;border-radius:3px;'>{line[2:]}</span>",
                    unsafe_allow_html=True,
                )
        elif line.startswith("  "):
            text = line[2:]
            with col1:
                st.text(text)
            with col2:
                st.text(text)


def render_bullet_diff(bullets: list[dict]):
    """Render individual bullet diffs with rationale."""
    for i, bullet in enumerate(bullets):
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                st.caption("Original")
                st.markdown(
                    f"<span style='background-color:#fff3f3;padding:4px 8px;border-radius:4px;display:block;'>{bullet.get('original', '')}</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.caption("Tailored")
                st.markdown(
                    f"<span style='background-color:#f3fff3;padding:4px 8px;border-radius:4px;display:block;'>{bullet.get('tailored', '')}</span>",
                    unsafe_allow_html=True,
                )
            rationale = bullet.get("rationale", "")
            if rationale:
                st.caption(f"💡 {rationale}")


def render_section_diff(section_name: str, original: str, tailored: str):
    """Render a section-level diff."""
    with st.container(border=True):
        st.markdown(f"**{section_name}**")
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Original")
            st.text(original[:500] if original else "(empty)")
        with col2:
            st.caption("Tailored")
            st.text(tailored[:500] if tailored else "(empty)")
