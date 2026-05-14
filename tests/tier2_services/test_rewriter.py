"""
Tier 2 — Core service tests for rewriter.py.
Tests prompt building, diff computation, JSON fallback, and full pipeline.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from services.rewrite.rewriter import (
    RewriteResult,
    _format_structured_resume,
    _build_prompt,
    _compute_diff,
    _extract_json_fallback,
    _get_vllm_client,
    _call_vllm,
    rewrite_resume_for_job,
)
from services.rewrite.schema import RewriteOutput, TailoredBullet, TailoredExperience


class TestFormatStructuredResume:
    def test_full_structured(self, sample_resume_payload):
        result = _format_structured_resume(sample_resume_payload["structured"])
        assert "Jane Doe" in result
        assert "Security Analyst" in result
        assert "Tech Corp" in result
        assert "Splunk SIEM" in result
        assert "CISSP" in result
        assert "Skills:" in result

    def test_minimal_structured(self):
        minimal = {"contact_info": {"name": "John"}, "summary": "A summary"}
        result = _format_structured_resume(minimal)
        assert "John" in result
        assert "A summary" in result

    def test_empty_structured(self):
        result = _format_structured_resume({})
        assert result == ""

    def test_no_contact_info(self):
        result = _format_structured_resume({"summary": "Just summary"})
        assert "Just summary" in result


class TestBuildPrompt:
    def test_returns_system_and_user_prompts(self, sample_job_payload, sample_resume_payload):
        system, user = _build_prompt(sample_job_payload, sample_resume_payload)
        assert isinstance(system, str)
        assert isinstance(user, str)
        assert len(system) > 0
        assert len(user) > 0

    def test_user_prompt_contains_job_info(self, sample_job_payload, sample_resume_payload):
        _, user = _build_prompt(sample_job_payload, sample_resume_payload)
        assert "Senior Cybersecurity Engineer" in user
        assert "Acme Defense Corp" in user
        assert "Washington, DC" in user

    def test_user_prompt_contains_resume_info(self, sample_job_payload, sample_resume_payload):
        _, user = _build_prompt(sample_job_payload, sample_resume_payload)
        assert "Jane Doe" in user or "jane@example.com" in user

    def test_uses_structured_when_available(self, sample_job_payload, sample_resume_payload):
        """When structured data exists, it should be formatted instead of raw_text."""
        payload_with_structured = dict(sample_resume_payload)
        payload_with_structured["structured"] = sample_resume_payload["structured"]
        _, user = _build_prompt(sample_job_payload, payload_with_structured)
        # Should contain formatted structured data
        assert "Security Analyst" in user

    def test_falls_back_to_raw_text(self, sample_job_payload):
        resume = {"raw_text": "Plain text resume content"}
        _, user = _build_prompt(sample_job_payload, resume)
        assert "Plain text resume content" in user


class TestComputeDiff:
    def test_summary_diff(self):
        rewrite = RewriteOutput(tailored_summary="New summary", overall_rationale="ok")
        original = {"summary": "Old summary"}
        diffs = _compute_diff(original, rewrite)
        summary_diffs = [d for d in diffs if d["section"] == "summary"]
        assert len(summary_diffs) == 1
        assert summary_diffs[0]["original"] == "Old summary"
        assert summary_diffs[0]["tailored"] == "New summary"

    def test_experience_bullet_diffs(self):
        rewrite = RewriteOutput(
            experience=[
                TailoredExperience(
                    title="Engineer",
                    company="Corp",
                    bullets=[
                        TailoredBullet(original="orig1", tailored="new1", rationale="better"),
                        TailoredBullet(original="orig2", tailored="new2"),
                    ],
                )
            ],
            overall_rationale="ok",
        )
        original = {"summary": ""}
        diffs = _compute_diff(original, rewrite)
        bullet_diffs = [d for d in diffs if d["section"].startswith("experience:")]
        assert len(bullet_diffs) == 2
        assert bullet_diffs[0]["original"] == "orig1"
        assert bullet_diffs[0]["tailored"] == "new1"
        assert bullet_diffs[0]["rationale"] == "better"

    def test_skills_highlighted_diff(self):
        rewrite = RewriteOutput(
            skills_highlighted=["SIEM", "Splunk"],
            overall_rationale="ok",
        )
        original = {"skills": ["Python"]}
        diffs = _compute_diff(original, rewrite)
        skill_diffs = [d for d in diffs if d["section"] == "skills_highlighted"]
        assert len(skill_diffs) == 1
        assert skill_diffs[0]["tailored"] == ["SIEM", "Splunk"]

    def test_certifications_emphasized_diff(self):
        rewrite = RewriteOutput(
            certifications_emphasized=["CISSP"],
            overall_rationale="ok",
        )
        original = {}
        diffs = _compute_diff(original, rewrite)
        cert_diffs = [d for d in diffs if d["section"] == "certifications_emphasized"]
        assert len(cert_diffs) == 1
        assert cert_diffs[0]["tailored"] == ["CISSP"]

    def test_empty_rewrite(self):
        rewrite = RewriteOutput(overall_rationale="ok")
        original = {}
        diffs = _compute_diff(original, rewrite)
        assert diffs == []

    def test_no_summary_when_empty(self):
        rewrite = RewriteOutput(tailored_summary="", overall_rationale="ok")
        original = {"summary": "old"}
        diffs = _compute_diff(original, rewrite)
        summary_diffs = [d for d in diffs if d["section"] == "summary"]
        assert len(summary_diffs) == 0


class TestExtractJsonFallback:
    def test_valid_json_in_text(self):
        content = 'Some text {"tailored_summary": "hi", "overall_rationale": "ok"} more text'
        result = _extract_json_fallback(content)
        assert result.tailored_summary == "hi"

    def test_no_json(self):
        result = _extract_json_fallback("Just plain text, no JSON here")
        assert "Error" in result.overall_rationale

    def test_malformed_json(self):
        result = _extract_json_fallback('{"tailored_summary": "hi", broken}')
        assert "Error" in result.overall_rationale

    def test_json_without_required_fields(self):
        content = '{"some_other_field": "value"}'
        result = _extract_json_fallback(content)
        # Should still return a RewriteOutput with defaults
        assert isinstance(result, RewriteOutput)


class TestRewriteResumeForJob:
    def test_full_pipeline(self, mock_embedding, mock_vllm_client,
                           sample_job_payload, sample_resume_payload):
        from unittest.mock import patch
        # Setup Qdrant mocks for job and resume fetching
        mock_job_record = MagicMock()
        mock_job_record.id = "job-123"
        mock_job_record.payload = sample_job_payload

        mock_resume_record = MagicMock()
        mock_resume_record.id = "resume-456"
        mock_resume_record.payload = sample_resume_payload

        mock_client = MagicMock()
        mock_client.collection_exists.return_value = True

        # scroll returns different results based on collection
        def scroll_side_effect(*args, **kwargs):
            collection = kwargs.get("collection_name", args[0] if args else "")
            if "jobs" in str(collection):
                return ([mock_job_record], None)
            else:
                return ([mock_resume_record], None)

        mock_client.scroll.side_effect = scroll_side_effect

        # Mock search for match score
        from qdrant_client.models import ScoredPoint
        mock_client.search.return_value = [
            ScoredPoint(id="job-123", version=0, score=0.88, payload=sample_job_payload),
        ]

        with patch("services.rewrite.rewriter._fetch_job_and_resume",
                   return_value=(sample_job_payload, sample_resume_payload)), \
             patch("services.rewrite.rewriter.match_jobs_to_resume",
                   return_value=[MagicMock(job_id="job-123", score=0.88)]):
            result = rewrite_resume_for_job("resume-456", "job-123")

        assert isinstance(result, RewriteResult)
        assert result.job_title == "Senior Cybersecurity Engineer"
        assert result.company == "Acme Defense Corp"
        assert result.match_score == 0.88
        assert "tailored_summary" in result.tailored_resume
        assert len(result.diff) > 0

    def test_job_not_found_raises(self, mock_qdrant_client):
        mock_qdrant_client.retrieve.return_value = []

        with pytest.raises(ValueError, match="Job not found"):
            rewrite_resume_for_job("resume-1", "nonexistent-job")


class TestVLLMClient:
    def test_get_vllm_client_returns_openai_client(self):
        client = _get_vllm_client()
        assert client is not None
        assert hasattr(client, "chat")

    def test_call_vllm(self):
        import json
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()

        sample = RewriteOutput(
            tailored_summary="Test summary",
            skills_highlighted=["SIEM"],
            overall_rationale="Good",
        )
        mock_message.content = json.dumps(sample.model_dump())
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("services.rewrite.rewriter._get_vllm_client", return_value=mock_client):
            result = _call_vllm("system prompt", "user prompt")
            assert isinstance(result, RewriteOutput)
            assert result.tailored_summary == "Test summary"
            assert result.skills_highlighted == ["SIEM"]

    def test_call_vllm_json_fallback(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "not valid json at all"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("services.rewrite.rewriter._get_vllm_client", return_value=mock_client):
            result = _call_vllm("system", "user")
            assert isinstance(result, RewriteOutput)
            assert "Error" in result.overall_rationale

    def test_call_vllm_request_structure(self):
        """Verify the request sent to vLLM has correct deterministic params."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()

        import json
        sample = RewriteOutput(overall_rationale="ok")
        mock_message.content = json.dumps(sample.model_dump())
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        with patch("services.rewrite.rewriter._get_vllm_client", return_value=mock_client):
            _call_vllm("system", "user")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["top_p"] == 1.0
        assert call_kwargs["seed"] == 42
        assert "extra_body" in call_kwargs
