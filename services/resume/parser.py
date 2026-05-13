"""
Resume Parser — Parse PDF, DOCX, TXT files and structured JSON.
"""
import io
from loguru import logger

from services.scraper.metadata_extractor import extract_all_metadata


def parse_pdf(content: bytes) -> str:
    """Extract text from PDF bytes using PyMuPDF."""
    import fitz  # PyMuPDF
    doc = fitz.open(stream=content, filetype="pdf")
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def parse_docx(content: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    from docx import Document
    doc = Document(io.BytesIO(content))
    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text)
    return "\n".join(text_parts)


def parse_txt(content: bytes) -> str:
    """Decode plain text bytes."""
    return content.decode("utf-8", errors="replace")


def parse_resume_file(content: bytes, filename: str) -> dict:
    """
    Parse a resume file and return structured data.
    Supports PDF, DOCX, and TXT formats.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        raw_text = parse_pdf(content)
    elif ext in ("docx", "doc"):
        raw_text = parse_docx(content)
    elif ext in ("txt", "text", "md"):
        raw_text = parse_txt(content)
    else:
        raise ValueError(f"Unsupported file format: .{ext}")

    if not raw_text.strip():
        raise ValueError("No text could be extracted from the file")

    metadata = extract_all_metadata(raw_text)

    return {
        "raw_text": raw_text,
        "structured": None,  # Could add LLM-based structuring here
        **metadata,
    }


def parse_resume_json(data: dict) -> dict:
    """
    Process a structured JSON resume into searchable text.
    """
    parts = []

    contact = data.get("contact_info", {})
    if contact:
        parts.append(
            f"{contact.get('name', '')}\n"
            f"{contact.get('email', '')}\n"
            f"{contact.get('location', '')}"
        )

    summary = data.get("summary", "")
    if summary:
        parts.append(summary)

    for exp in data.get("experience", []):
        parts.append(
            f"{exp.get('title', '')} at {exp.get('company', '')}\n"
            + "\n".join(exp.get("bullets", []))
        )

    for edu in data.get("education", []):
        parts.append(f"{edu.get('degree', '')} - {edu.get('school', '')}")

    for cert in data.get("certifications", []):
        parts.append(cert.get("name", ""))

    skills = data.get("skills", [])
    if skills:
        parts.append("Skills: " + ", ".join(skills))

    raw_text = "\n\n".join(parts)
    metadata = extract_all_metadata(raw_text)

    return {
        "raw_text": raw_text,
        "structured": data,
        **metadata,
    }
