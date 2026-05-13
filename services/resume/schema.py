"""
Resume Schema — Pydantic models for structured resume representation.
"""
from pydantic import BaseModel
from typing import Optional


class ContactInfo(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    website: str = ""


class Experience(BaseModel):
    title: str
    company: str
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = []


class Education(BaseModel):
    degree: str
    school: str
    graduation_year: str = ""
    gpa: str = ""


class Certification(BaseModel):
    name: str
    issuer: str = ""
    date: str = ""


class ResumeSchema(BaseModel):
    contact_info: ContactInfo = ContactInfo()
    summary: str = ""
    experience: list[Experience] = []
    education: list[Education] = []
    certifications: list[Certification] = []
    skills: list[str] = []
    clearance_level: str = ""


class TailoredBullet(BaseModel):
    original: str
    tailored: str
    rationale: str = ""


class TailoredExperience(BaseModel):
    title: str
    company: str
    bullets: list[TailoredBullet]


class TailoredResume(BaseModel):
    """Output schema for LLM resume rewrite."""
    summary: str = ""
    experience: list[TailoredExperience] = []
    skills_highlighted: list[str] = []
    certifications_emphasized: list[str] = []
    overall_rationale: str = ""
