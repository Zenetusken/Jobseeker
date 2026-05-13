"""
DOM Mapper — Intelligently maps JSON resume fields to HTML form elements.
Uses label text matching, placeholder heuristics, and common field name patterns.
"""
import re
from typing import Optional
from loguru import logger


# Common form field name patterns mapped to resume JSON keys
FIELD_PATTERNS: dict[str, list[str]] = {
    "first_name": ["first.name", "firstname", "given.name", "fname", "first_name"],
    "last_name": ["last.name", "lastname", "surname", "family.name", "lname", "last_name"],
    "email": ["email", "e-mail", "email.address", "email_address"],
    "phone": ["phone", "telephone", "mobile", "cell", "phone.number", "phone_number"],
    "location": ["location", "city", "address", "residence"],
    "linkedin": ["linkedin", "linkedin.url", "linkedin_url", "profile"],
    "cover_letter_upload": ["cover.letter", "cover_letter", "cl", "cover"],
    "summary": ["summary", "objective", "about", "bio", "description"],
    "skills": ["skills", "technical.skills", "qualifications", "competencies", "keywords"],
    "experience": ["experience", "work.history", "employment", "work_experience"],
    "education": ["education", "academic", "degree", "university", "school"],
    "certifications": ["certifications", "certificates", "licenses", "certs"],
    "resume_upload": ["resume", "cv", "upload", "attach", "file", "document", "resume.upload"],
}


def normalize_field_name(name: str) -> str:
    """Normalize a field name for matching."""
    return re.sub(r'[^a-z0-9.]', '.', name.lower().strip())


def match_field_to_resume_key(field_name: str) -> Optional[str]:
    """
    Match an HTML form field name/label to a resume JSON key.
    Returns the resume key or None.
    """
    normalized = normalize_field_name(field_name)
    if not normalized:
        return None

    for resume_key, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            pattern_norm = normalize_field_name(pattern)
            if pattern_norm in normalized or normalized in pattern_norm:
                return resume_key

    return None


def extract_value_for_field(resume_key: str, tailored_resume: dict) -> Optional[str]:
    """
    Extract the appropriate value from the tailored resume for a given field key.
    """
    contact = tailored_resume.get("contact_info", {})

    if resume_key == "first_name":
        name = contact.get("name", "")
        return name.split()[0] if name else None
    elif resume_key == "last_name":
        name = contact.get("name", "")
        parts = name.split()
        return " ".join(parts[1:]) if len(parts) > 1 else None
    elif resume_key in ("email", "phone", "location", "linkedin"):
        return contact.get(resume_key)
    elif resume_key == "summary":
        return tailored_resume.get("tailored_summary", "")
    elif resume_key == "skills":
        skills = tailored_resume.get("skills_highlighted", [])
        return ", ".join(skills) if skills else None
    elif resume_key == "experience":
        # Format experience as text
        exps = tailored_resume.get("experience", [])
        lines = []
        for exp in exps:
            lines.append(f"{exp.get('title', '')} at {exp.get('company', '')}")
            for b in exp.get("bullets", []):
                lines.append(f"  - {b.get('tailored', b.get('original', ''))}")
        return "\n".join(lines) if lines else None
    elif resume_key == "certifications":
        certs = tailored_resume.get("certifications_emphasized", [])
        return ", ".join(certs) if certs else None

    return None


def build_field_mapping(page) -> dict[str, str]:
    """
    Scan the page for form fields and build a mapping from
    resume keys to CSS selectors.
    Returns {resume_key: selector}.
    """
    mapping = {}

    # Common input selectors
    input_selectors = [
        "input[type='text']",
        "input[type='email']",
        "input[type='tel']",
        "input:not([type])",
        "textarea",
        "select",
    ]

    for selector in input_selectors:
        elements = page.query_selector_all(selector)
        for el in elements:
            # Try multiple ways to identify the field
            name = el.get_attribute("name") or ""
            id_attr = el.get_attribute("id") or ""
            placeholder = el.get_attribute("placeholder") or ""
            aria_label = el.get_attribute("aria-label") or ""

            # Also check associated label
            label_text = ""
            label_el = page.query_selector(f"label[for='{id_attr}']")
            if label_el:
                label_text = label_el.inner_text()

            # Try to match
            for attr in [name, id_attr, placeholder, aria_label, label_text]:
                if attr:
                    resume_key = match_field_to_resume_key(attr)
                    if resume_key and resume_key not in mapping:
                        mapping[resume_key] = selector
                        logger.debug(f"Mapped '{attr}' -> {resume_key}")
                        break

    return mapping
