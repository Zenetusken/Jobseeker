"""
PDF Generator — Dynamically generates a PDF of the tailored resume.
Uses ReportLab for PDF creation from the tailored resume JSON.
"""
import io
import datetime
from loguru import logger

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
    HRFlowable,
)


def _build_pdf_story(tailored_resume: dict) -> tuple:
    """
    Build the ReportLab story (flowables list) and document template
    for a tailored resume. Returns (doc, story, buffer).
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    name_style = ParagraphStyle(
        "Name",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=4,
        textColor=HexColor("#1a1a2e"),
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=14,
        spaceAfter=6,
        textColor=HexColor("#16213e"),
        borderPadding=(0, 0, 2, 0),
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=styles["Normal"],
        fontSize=10,
        leftIndent=20,
        spaceAfter=3,
    )
    normal_style = ParagraphStyle(
        "Normal2",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
    )

    story = []

    # Contact info
    contact = tailored_resume.get("contact_info", {})
    name = contact.get("name", "Candidate Name")
    story.append(Paragraph(name, name_style))
    contact_line = (
        f"{contact.get('email', '')} | "
        f"{contact.get('phone', '')} | "
        f"{contact.get('location', '')}"
    )
    story.append(Paragraph(contact_line, normal_style))
    if contact.get("linkedin"):
        story.append(Paragraph(contact["linkedin"], normal_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#0f3460")))
    story.append(Spacer(1, 8))

    # Summary
    summary = tailored_resume.get("tailored_summary", "")
    if summary:
        story.append(Paragraph("Professional Summary", section_style))
        story.append(Paragraph(summary, normal_style))

    # Skills
    skills = tailored_resume.get("skills_highlighted", [])
    if skills:
        story.append(Paragraph("Technical Skills", section_style))
        story.append(Paragraph(", ".join(skills), normal_style))

    # Certifications
    certs = tailored_resume.get("certifications_emphasized", [])
    if certs:
        story.append(Paragraph("Certifications", section_style))
        story.append(Paragraph(", ".join(certs), normal_style))

    # Experience
    experience = tailored_resume.get("experience", [])
    if experience:
        story.append(Paragraph("Professional Experience", section_style))
        for exp in experience:
            exp_header = f"<b>{exp.get('title', '')}</b> — {exp.get('company', '')}"
            story.append(Paragraph(exp_header, normal_style))
            bullets = exp.get("bullets", [])
            bullet_items = [
                ListItem(Paragraph(b.get("tailored", b.get("original", "")), bullet_style))
                for b in bullets
            ]
            if bullet_items:
                story.append(ListFlowable(
                    bullet_items,
                    bulletType="bullet",
                    start="-",
                    leftIndent=20,
                    bulletFontSize=8,
                ))
            story.append(Spacer(1, 6))

    # Education
    education = tailored_resume.get("education", [])
    if education:
        story.append(Paragraph("Education", section_style))
        for edu in education:
            edu_text = f"<b>{edu.get('degree', '')}</b> — {edu.get('school', '')}"
            story.append(Paragraph(edu_text, normal_style))

    return doc, story, buffer


def generate_pdf_bytes(tailored_resume: dict) -> bytes:
    """Generate PDF as bytes (for in-memory use)."""
    doc, story, buffer = _build_pdf_story(tailored_resume)
    doc.build(story)
    return buffer.getvalue()


def generate_tailored_resume_pdf(tailored_resume: dict, output_path: str) -> str:
    """
    Generate a professional PDF from the tailored resume JSON.
    Returns the output file path.
    """
    pdf_bytes = generate_pdf_bytes(tailored_resume)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)
    logger.info(f"PDF generated: {output_path}")
    return output_path
