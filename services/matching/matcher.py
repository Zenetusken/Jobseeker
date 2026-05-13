"""
Matching Engine — Two-tier job-resume matching.
Tier 1: Vector similarity search via Qdrant.
Tier 2: Hard metadata filter (certs, clearance, skills).
"""
from dataclasses import dataclass, field
from loguru import logger

from services.embeddings.embedding_service import encode_text
from services.qdrant.init_collections import get_qdrant_client
from config.settings import settings


@dataclass
class MatchResult:
    job_id: str
    title: str
    company: str
    location: str
    score: float
    required_certs: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    clearance_level: str = ""
    url: str = ""
    description: str = ""
    hard_filter_pass: bool = True
    missing_certs: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "score": round(self.score, 4),
            "required_certs": self.required_certs,
            "required_skills": self.required_skills,
            "clearance_level": self.clearance_level,
            "url": self.url,
            "description": self.description,
            "hard_filter_pass": self.hard_filter_pass,
            "missing_certs": self.missing_certs,
            "missing_skills": self.missing_skills,
        }


def _get_resume_payload(resume_id: str) -> dict:
    """Retrieve resume payload from Qdrant."""
    client = get_qdrant_client()
    records, _ = client.scroll(
        collection_name=settings.qdrant_collection_resumes,
        limit=100,
        with_payload=True,
        with_vectors=False,
    )
    for r in records:
        if str(r.id) == str(resume_id):
            return r.payload or {}
    raise ValueError(f"Resume not found: {resume_id}")


def _hard_filter(resume_payload: dict, job_payload: dict) -> tuple[bool, list[str], list[str]]:
    """
    Apply hard metadata filter.
    Returns (passes, missing_certs, missing_skills).
    """
    resume_certs = set(resume_payload.get("certs", []))
    resume_skills = set(resume_payload.get("skills", []))
    resume_clearance = resume_payload.get("clearance_level", "")

    job_certs = set(job_payload.get("required_certs", []))
    job_skills = set(job_payload.get("required_skills", []))
    job_clearance = job_payload.get("clearance_level", "")

    missing_certs = list(job_certs - resume_certs)
    missing_skills = list(job_skills - resume_skills)

    # Check clearance: if job requires clearance and resume doesn't have it
    clearance_mismatch = False
    if job_clearance:
        clearance_levels = ["Top Secret", "Secret", "Confidential", "Public Trust"]
        if resume_clearance not in clearance_levels:
            clearance_mismatch = True
        elif job_clearance in clearance_levels and resume_clearance in clearance_levels:
            # Higher clearance satisfies lower
            job_idx = clearance_levels.index(job_clearance)
            resume_idx = clearance_levels.index(resume_clearance)
            if resume_idx > job_idx:
                clearance_mismatch = True

    passes = len(missing_certs) == 0 and not clearance_mismatch
    return passes, missing_certs, missing_skills


def match_jobs_to_resume(
    resume_id: str,
    top_k: int = 10,
    min_score: float = 0.3,
) -> list[MatchResult]:
    """
    Find top matching jobs for a resume.
    1. Get resume embedding
    2. Vector search in Qdrant
    3. Apply hard metadata filters
    """
    resume_payload = _get_resume_payload(resume_id)
    resume_text = resume_payload.get("raw_text", "")
    if not resume_text:
        raise ValueError("Resume has no text content")

    # Generate embedding for the resume text
    resume_embedding = encode_text(resume_text)

    # Vector search
    client = get_qdrant_client()
    search_results = client.search(
        collection_name=settings.qdrant_collection_jobs,
        query_vector=resume_embedding,
        limit=top_k * 3,  # Over-fetch to account for hard-filter drops
        with_payload=True,
    )

    matches: list[MatchResult] = []
    for hit in search_results:
        if hit.score < min_score:
            continue

        payload = hit.payload or {}
        passes, missing_certs, missing_skills = _hard_filter(resume_payload, payload)

        match = MatchResult(
            job_id=str(hit.id),
            title=payload.get("title", ""),
            company=payload.get("company", ""),
            location=payload.get("location", ""),
            score=hit.score,
            required_certs=payload.get("required_certs", []),
            required_skills=payload.get("required_skills", []),
            clearance_level=payload.get("clearance_level", ""),
            url=payload.get("url", ""),
            description=payload.get("description", ""),
            hard_filter_pass=passes,
            missing_certs=missing_certs,
            missing_skills=missing_skills,
        )
        matches.append(match)

    # Sort: hard-filter-passing first, then by score
    matches.sort(key=lambda m: (not m.hard_filter_pass, -m.score))
    return matches[:top_k]
