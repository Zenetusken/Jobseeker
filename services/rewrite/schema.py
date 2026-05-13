"""
Rewrite Schema — Pydantic models for the LLM rewrite output.
Used by Outlines to enforce JSON structure at generation time.
"""
from pydantic import BaseModel
from typing import Optional


class TailoredBullet(BaseModel):
    original: str
    tailored: str
    rationale: str = ""


class TailoredExperience(BaseModel):
    title: str
    company: str
    bullets: list[TailoredBullet]


class RewriteOutput(BaseModel):
    """The exact JSON structure the LLM must produce."""
    tailored_summary: str = ""
    experience: list[TailoredExperience] = []
    skills_highlighted: list[str] = []
    certifications_emphasized: list[str] = []
    overall_rationale: str = ""


# The prompt template for resume rewriting
REWRITE_SYSTEM_PROMPT = """You are an expert cybersecurity resume writer. Your task is to tailor a candidate's resume to match a specific job description.

CRITICAL RULES:
1. NEVER invent or fabricate any experience, certification, skill, or qualification the candidate does not have.
2. ONLY rephrase, reorder, and emphasize existing content to better match the job requirements.
3. Use the exact cybersecurity and networking terminology from the job description where applicable.
4. Map the candidate's real experience to the job's required skills using precise technical language.
5. Output MUST be valid JSON matching the exact schema provided.
6. Do NOT add any text before or after the JSON output."""

REWRITE_USER_PROMPT_TEMPLATE = """## Job Description
Title: {job_title}
Company: {job_company}
Location: {job_location}

{job_description}

## Candidate's Current Resume
{resume_text}

## Instructions
Rewrite the candidate's resume to maximize alignment with this job. For each experience bullet:
- original: the exact original bullet text
- tailored: the rewritten version emphasizing relevant skills and using job-specific terminology
- rationale: brief explanation of the change (1 sentence)

Highlight the most relevant skills and certifications. Provide an overall rationale for the changes.

Output ONLY valid JSON matching this schema:
{json_schema}"""
