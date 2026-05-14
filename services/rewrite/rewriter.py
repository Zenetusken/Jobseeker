"""
LLM Resume Rewriter — Core inference service.
Calls Foundation-Sec-8B via vLLM with deterministic parameters (T=0.0)
and Outlines pre-generation JSON constraints.
"""
import json
from dataclasses import dataclass, field
from openai import OpenAI
from loguru import logger

from config.settings import settings
from services.rewrite.schema import (
    RewriteOutput,
    REWRITE_SYSTEM_PROMPT,
    REWRITE_USER_PROMPT_TEMPLATE,
)
from services.rewrite.outlines_constraint import (
    get_json_schema_for_prompt,
    apply_outlines_constraint_to_request,
)
from services.qdrant.init_collections import get_qdrant_client
from services.matching.matcher import match_jobs_to_resume


@dataclass
class RewriteResult:
    job_title: str
    company: str
    original_resume: dict
    tailored_resume: dict
    diff: list[dict]
    match_score: float


def _get_vllm_client() -> OpenAI:
    """Create an OpenAI-compatible client pointed at vLLM."""
    return OpenAI(
        base_url=settings.vllm_base_url,
        api_key="not-needed",  # vLLM doesn't require auth locally
    )


def _fetch_job_and_resume(job_id: str, resume_id: str) -> tuple[dict, dict]:
    """Fetch job and resume payloads from Qdrant by ID (O(1) lookups)."""
    client = get_qdrant_client()

    job_results = client.retrieve(
        collection_name=settings.qdrant_collection_jobs,
        ids=[job_id],
        with_payload=True,
        with_vectors=False,
    )
    if not job_results:
        raise ValueError(f"Job not found: {job_id}")
    job_payload = job_results[0].payload or {}

    resume_results = client.retrieve(
        collection_name=settings.qdrant_collection_resumes,
        ids=[resume_id],
        with_payload=True,
        with_vectors=False,
    )
    if not resume_results:
        raise ValueError(f"Resume not found: {resume_id}")
    resume_payload = resume_results[0].payload or {}

    return job_payload, resume_payload


def _build_prompt(job_payload: dict, resume_payload: dict) -> tuple[str, str]:
    """Build system and user prompts for the LLM."""
    resume_text = resume_payload.get("raw_text", "")
    structured = resume_payload.get("structured")

    # If we have structured data, format it nicely
    if structured:
        resume_text = _format_structured_resume(structured)

    json_schema_desc = get_json_schema_for_prompt()

    user_prompt = REWRITE_USER_PROMPT_TEMPLATE.format(
        job_title=job_payload.get("title", ""),
        job_company=job_payload.get("company", ""),
        job_location=job_payload.get("location", ""),
        job_description=job_payload.get("description", ""),
        resume_text=resume_text,
        json_schema=json_schema_desc,
    )

    return REWRITE_SYSTEM_PROMPT, user_prompt


def _format_structured_resume(structured: dict) -> str:
    """Format a structured resume dict into readable text for the prompt."""
    parts = []

    contact = structured.get("contact_info", {})
    if contact:
        parts.append(f"Name: {contact.get('name', '')}")

    summary = structured.get("summary", "")
    if summary:
        parts.append(f"Summary: {summary}")

    for exp in structured.get("experience", []):
        parts.append(
            f"\n{exp.get('title', '')} at {exp.get('company', '')} "
            f"({exp.get('start_date', '')} - {exp.get('end_date', '')})"
        )
        for bullet in exp.get("bullets", []):
            parts.append(f"  - {bullet}")

    for edu in structured.get("education", []):
        parts.append(f"\n{edu.get('degree', '')} - {edu.get('school', '')}")

    certs = structured.get("certifications", [])
    if certs:
        parts.append("\nCertifications:")
        for cert in certs:
            parts.append(f"  - {cert.get('name', '')}")

    skills = structured.get("skills", [])
    if skills:
        parts.append(f"\nSkills: {', '.join(skills)}")

    return "\n".join(parts)


def _call_vllm(system_prompt: str, user_prompt: str) -> RewriteOutput:
    """
    Call vLLM with deterministic parameters and JSON constraint.
    Temperature=0.0 ensures greedy decoding — no creativity, no hallucination.
    """
    client = _get_vllm_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    request_kwargs = {
        "model": settings.vllm_model_name,
        "messages": messages,
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 2048,
        "seed": 42,  # Deterministic seed
    }

    # Apply Outlines pre-generation JSON constraint
    request_kwargs = apply_outlines_constraint_to_request(request_kwargs)

    logger.info("Calling vLLM for resume rewrite (T=0.0, guided_json)...")
    response = client.chat.completions.create(**request_kwargs)

    content = response.choices[0].message.content
    logger.info(f"vLLM response received ({len(content)} chars)")

    # Parse the guaranteed-valid JSON.
    # If this raises, the Outlines FSM constraint was violated — that is
    # mathematically impossible under correct guided decoding, so we treat
    # it as a hard infrastructure failure, not a recoverable condition.
    try:
        data = json.loads(content)
        return RewriteOutput(**data)
    except json.JSONDecodeError as e:
        logger.critical(
            f"Outlines FSM constraint violated — vLLM returned non-JSON despite "
            f"guided_json constraint. Raw content (first 500 chars): {content[:500]!r}"
        )
        raise RuntimeError(
            f"Outlines FSM constraint violated: malformed JSON received despite "
            f"guided_json constraint. Parse error: {e}"
        ) from e
    except Exception as e:
        logger.critical(
            f"Outlines FSM constraint violated — RewriteOutput validation failed "
            f"despite guided_json constraint. Error: {e}. "
            f"Raw content (first 500 chars): {content[:500]!r}"
        )
        raise RuntimeError(
            f"Outlines FSM constraint violated: JSON parsed but failed RewriteOutput "
            f"schema validation. Validation error: {e}"
        ) from e


def _compute_diff(original_resume: dict, rewrite: RewriteOutput) -> list[dict]:
    """Compute a structured diff between original and tailored resume."""
    diffs = []

    if rewrite.tailored_summary:
        diffs.append({
            "section": "summary",
            "original": original_resume.get("summary", ""),
            "tailored": rewrite.tailored_summary,
            "type": "modified",
        })

    for exp in rewrite.experience:
        for bullet in exp.bullets:
            diffs.append({
                "section": f"experience: {exp.title} @ {exp.company}",
                "original": bullet.original,
                "tailored": bullet.tailored,
                "rationale": bullet.rationale,
                "type": "modified",
            })

    if rewrite.skills_highlighted:
        diffs.append({
            "section": "skills_highlighted",
            "original": original_resume.get("skills", []),
            "tailored": rewrite.skills_highlighted,
            "type": "emphasized",
        })

    if rewrite.certifications_emphasized:
        diffs.append({
            "section": "certifications_emphasized",
            "original": [],
            "tailored": rewrite.certifications_emphasized,
            "type": "emphasized",
        })

    return diffs


def rewrite_resume_for_job(
    resume_id: str,
    job_id: str,
    match_score: float = 0.0,
) -> RewriteResult:
    """
    Full rewrite pipeline:
    1. Fetch job + resume from Qdrant
    2. Build prompt with JSON schema
    3. Call vLLM with T=0.0 + Outlines constraint
    4. Parse output and compute diff

    Pass match_score if already known to avoid a redundant vector search.
    """
    job_payload, resume_payload = _fetch_job_and_resume(job_id, resume_id)

    # Only run vector search when caller didn't supply the score
    if match_score == 0.0:
        matches = match_jobs_to_resume(resume_id, top_k=100, min_score=0.0)
        for m in matches:
            if str(m.job_id) == str(job_id):
                match_score = m.score
                break

    system_prompt, user_prompt = _build_prompt(job_payload, resume_payload)
    rewrite = _call_vllm(system_prompt, user_prompt)

    # Build original resume representation
    original_resume = {
        "summary": resume_payload.get("raw_text", "")[:500],
        "structured": resume_payload.get("structured"),
    }

    tailored_resume = rewrite.model_dump()
    diff = _compute_diff(original_resume, rewrite)

    return RewriteResult(
        job_title=job_payload.get("title", ""),
        company=job_payload.get("company", ""),
        original_resume=original_resume,
        tailored_resume=tailored_resume,
        diff=diff,
        match_score=match_score,
    )
