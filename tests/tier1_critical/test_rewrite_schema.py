"""
Tier 1 — Critical pure-logic tests for rewrite/schema.py.
Tests RewriteOutput model validation and prompt templates.
"""
import pytest
from pydantic import ValidationError
from services.rewrite.schema import (
    RewriteOutput,
    TailoredBullet,
    TailoredExperience,
    REWRITE_SYSTEM_PROMPT,
    REWRITE_USER_PROMPT_TEMPLATE,
)


class TestTailoredBullet:
    def test_valid_bullet(self):
        b = TailoredBullet(original="orig", tailored="tailored", rationale="better match")
        assert b.original == "orig"
        assert b.tailored == "tailored"
        assert b.rationale == "better match"

    def test_rationale_defaults_to_empty(self):
        b = TailoredBullet(original="orig", tailored="tailored")
        assert b.rationale == ""

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            TailoredBullet(original="orig")  # missing tailored

    def test_missing_original_raises(self):
        with pytest.raises(ValidationError):
            TailoredBullet(tailored="tailored")


class TestTailoredExperience:
    def test_valid_experience(self):
        bullets = [TailoredBullet(original="a", tailored="b")]
        exp = TailoredExperience(title="Engineer", company="Corp", bullets=bullets)
        assert exp.title == "Engineer"
        assert exp.company == "Corp"
        assert len(exp.bullets) == 1

    def test_missing_bullets_raises(self):
        with pytest.raises(ValidationError):
            TailoredExperience(title="Engineer", company="Corp")


class TestRewriteOutput:
    def test_valid_minimal_output(self):
        output = RewriteOutput(overall_rationale="Good match")
        assert output.tailored_summary == ""
        assert output.experience == []
        assert output.skills_highlighted == []
        assert output.certifications_emphasized == []
        assert output.overall_rationale == "Good match"

    def test_valid_full_output(self):
        output = RewriteOutput(
            tailored_summary="Summary text",
            experience=[
                TailoredExperience(
                    title="Engineer",
                    company="Corp",
                    bullets=[TailoredBullet(original="a", tailored="b")],
                )
            ],
            skills_highlighted=["SIEM", "Splunk"],
            certifications_emphasized=["CISSP"],
            overall_rationale="Great fit",
        )
        assert len(output.experience) == 1
        assert output.experience[0].title == "Engineer"
        assert len(output.skills_highlighted) == 2

    def test_wrong_type_raises(self):
        with pytest.raises(ValidationError):
            RewriteOutput(skills_highlighted="not_a_list")

    def test_nested_wrong_type_raises(self):
        with pytest.raises(ValidationError):
            RewriteOutput(
                experience=[{"title": "Eng", "company": "Corp", "bullets": "not_a_list"}]
            )

    def test_model_dump(self):
        output = RewriteOutput(
            tailored_summary="Summary",
            skills_highlighted=["SIEM"],
            overall_rationale="Good",
        )
        dumped = output.model_dump()
        assert dumped["tailored_summary"] == "Summary"
        assert dumped["skills_highlighted"] == ["SIEM"]
        assert dumped["experience"] == []

    def test_model_json_schema(self):
        schema = RewriteOutput.model_json_schema()
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "tailored_summary" in schema["properties"]


class TestRewritePrompts:
    def test_system_prompt_contains_critical_rules(self):
        assert "NEVER invent" in REWRITE_SYSTEM_PROMPT
        assert "ONLY rephrase" in REWRITE_SYSTEM_PROMPT
        assert "valid JSON" in REWRITE_SYSTEM_PROMPT
        assert "Do NOT add any text before or after" in REWRITE_SYSTEM_PROMPT

    def test_system_prompt_is_non_empty(self):
        assert len(REWRITE_SYSTEM_PROMPT) > 100

    def test_user_prompt_template_has_all_placeholders(self):
        assert "{job_title}" in REWRITE_USER_PROMPT_TEMPLATE
        assert "{job_company}" in REWRITE_USER_PROMPT_TEMPLATE
        assert "{job_location}" in REWRITE_USER_PROMPT_TEMPLATE
        assert "{job_description}" in REWRITE_USER_PROMPT_TEMPLATE
        assert "{resume_text}" in REWRITE_USER_PROMPT_TEMPLATE
        assert "{json_schema}" in REWRITE_USER_PROMPT_TEMPLATE

    def test_user_prompt_format(self):
        result = REWRITE_USER_PROMPT_TEMPLATE.format(
            job_title="Security Engineer",
            job_company="Acme",
            job_location="Remote",
            job_description="Looking for SIEM expert",
            resume_text="Jane Doe - Security Analyst",
            json_schema='{"type": "object"}',
        )
        assert "Security Engineer" in result
        assert "Acme" in result
        assert "Remote" in result
        assert "Looking for SIEM expert" in result
        assert "Jane Doe" in result
        assert "json_schema" not in result  # placeholder should be replaced
