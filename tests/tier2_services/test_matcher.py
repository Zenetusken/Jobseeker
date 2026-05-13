"""
Tier 2 — Core service tests for matcher.py.
Tests hard_filter logic and match_jobs_to_resume with mocked Qdrant.
"""
import pytest
from unittest.mock import MagicMock, patch
from services.matching.matcher import (
    MatchResult,
    _hard_filter,
    match_jobs_to_resume,
)


class TestMatchResult:
    def test_to_dict_all_fields(self):
        mr = MatchResult(
            job_id="123",
            title="Security Engineer",
            company="Acme",
            location="Remote",
            score=0.85,
            required_certs=["CISSP"],
            required_skills=["SIEM"],
            clearance_level="Top Secret",
            url="https://example.com",
            description="Job desc",
            hard_filter_pass=True,
            missing_certs=[],
            missing_skills=[],
        )
        d = mr.to_dict()
        assert d["job_id"] == "123"
        assert d["title"] == "Security Engineer"
        assert d["score"] == 0.85
        assert d["hard_filter_pass"] is True

    def test_to_dict_score_rounding(self):
        mr = MatchResult(job_id="1", title="T", company="C", location="L", score=0.123456)
        d = mr.to_dict()
        assert d["score"] == 0.1235  # rounded to 4 decimal places


class TestHardFilter:
    def test_all_certs_match(self):
        resume = {"certs": ["CISSP", "CEH"]}
        job = {"required_certs": ["CISSP"]}
        passes, missing_certs, missing_skills = _hard_filter(resume, job)
        assert passes is True
        assert missing_certs == []

    def test_missing_cert(self):
        resume = {"certs": ["CEH"]}
        job = {"required_certs": ["CISSP"]}
        passes, missing_certs, missing_skills = _hard_filter(resume, job)
        assert passes is False
        assert "CISSP" in missing_certs

    def test_no_certs_required(self):
        resume = {"certs": []}
        job = {"required_certs": []}
        passes, missing_certs, missing_skills = _hard_filter(resume, job)
        assert passes is True

    def test_skills_mismatch_does_not_block(self):
        """Missing skills should be reported but not block the match."""
        resume = {"certs": ["CISSP"], "skills": ["Python"]}
        job = {"required_certs": ["CISSP"], "required_skills": ["SIEM", "Splunk"]}
        passes, missing_certs, missing_skills = _hard_filter(resume, job)
        assert passes is True  # skills don't block
        assert "SIEM" in missing_skills
        assert "Splunk" in missing_skills

    def test_clearance_top_secret_satisfies_secret(self):
        resume = {"certs": [], "clearance_level": "Top Secret"}
        job = {"required_certs": [], "clearance_level": "Secret"}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is True

    def test_clearance_secret_does_not_satisfy_top_secret(self):
        resume = {"certs": [], "clearance_level": "Secret"}
        job = {"required_certs": [], "clearance_level": "Top Secret"}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is False

    def test_clearance_top_secret_satisfies_top_secret(self):
        resume = {"certs": [], "clearance_level": "Top Secret"}
        job = {"required_certs": [], "clearance_level": "Top Secret"}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is True

    def test_no_clearance_required(self):
        resume = {"certs": [], "clearance_level": ""}
        job = {"required_certs": [], "clearance_level": ""}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is True

    def test_resume_has_no_clearance_but_job_requires(self):
        resume = {"certs": [], "clearance_level": ""}
        job = {"required_certs": [], "clearance_level": "Secret"}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is False

    def test_clearance_confidential_vs_secret(self):
        resume = {"certs": [], "clearance_level": "Confidential"}
        job = {"required_certs": [], "clearance_level": "Secret"}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is False  # Confidential is lower than Secret

    def test_clearance_public_trust_lowest(self):
        resume = {"certs": [], "clearance_level": "Public Trust"}
        job = {"required_certs": [], "clearance_level": "Confidential"}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is False

    def test_empty_payloads(self):
        passes, missing_certs, missing_skills = _hard_filter({}, {})
        assert passes is True
        assert missing_certs == []
        assert missing_skills == []

    @pytest.mark.parametrize("resume_clearance,job_clearance,expected", [
        ("Top Secret", "Top Secret", True),
        ("Top Secret", "Secret", True),
        ("Top Secret", "Confidential", True),
        ("Top Secret", "Public Trust", True),
        ("Secret", "Top Secret", False),
        ("Secret", "Secret", True),
        ("Secret", "Confidential", True),
        ("Confidential", "Secret", False),
        ("Confidential", "Confidential", True),
        ("Public Trust", "Confidential", False),
        ("Public Trust", "Public Trust", True),
        ("", "", True),
        ("", "Secret", False),
    ])
    def test_clearance_hierarchy_parametrized(self, resume_clearance, job_clearance, expected):
        resume = {"certs": [], "clearance_level": resume_clearance}
        job = {"required_certs": [], "clearance_level": job_clearance}
        passes, _, _ = _hard_filter(resume, job)
        assert passes is expected


class TestMatchJobsToResume:
    def test_returns_matches(self, mock_qdrant_client, mock_embedding):
        # Setup mock Qdrant to return a resume and job search results
        from qdrant_client.models import ScoredPoint

        # Mock resume scroll
        mock_qdrant_client.scroll.side_effect = [
            # First call: resume scroll
            ([MagicMock(id="resume-1", payload={
                "raw_text": "Security engineer with CISSP",
                "certs": ["CISSP"],
                "skills": ["SIEM"],
                "clearance_level": "Top Secret",
            })], None),
            # Second call: job search not via scroll but via search()
        ]

        # Mock search results
        mock_hit = ScoredPoint(
            id="job-1",
            version=0,
            score=0.85,
            payload={
                "title": "Security Engineer",
                "company": "Acme",
                "location": "Remote",
                "required_certs": ["CISSP"],
                "required_skills": ["SIEM"],
                "clearance_level": "Secret",
                "url": "https://example.com",
                "description": "Job desc",
            },
        )
        mock_qdrant_client.search.return_value = [mock_hit]

        results = match_jobs_to_resume("resume-1", top_k=10, min_score=0.3)
        assert len(results) == 1
        assert results[0].job_id == "job-1"
        assert results[0].title == "Security Engineer"
        assert results[0].score == 0.85
        assert results[0].hard_filter_pass is True

    def test_respects_min_score(self, mock_qdrant_client, mock_embedding):
        from qdrant_client.models import ScoredPoint

        mock_qdrant_client.scroll.return_value = (
            [MagicMock(id="resume-1", payload={"raw_text": "text", "certs": [], "skills": [], "clearance_level": ""})],
            None,
        )

        mock_qdrant_client.search.return_value = [
            ScoredPoint(id="job-1", version=0, score=0.2, payload={"title": "T", "company": "C", "required_certs": [], "required_skills": [], "clearance_level": ""}),
            ScoredPoint(id="job-2", version=0, score=0.9, payload={"title": "T2", "company": "C2", "required_certs": [], "required_skills": [], "clearance_level": ""}),
        ]

        results = match_jobs_to_resume("resume-1", top_k=10, min_score=0.5)
        assert len(results) == 1
        assert results[0].job_id == "job-2"

    def test_empty_resume_text_raises(self, mock_qdrant_client, mock_embedding):
        mock_qdrant_client.scroll.return_value = (
            [MagicMock(id="resume-1", payload={"raw_text": "", "certs": [], "skills": []})],
            None,
        )

        with pytest.raises(ValueError, match="no text content"):
            match_jobs_to_resume("resume-1")

    def test_resume_not_found_raises(self, mock_qdrant_client):
        mock_qdrant_client.scroll.return_value = ([], None)

        with pytest.raises(ValueError, match="Resume not found"):
            match_jobs_to_resume("nonexistent")

    def test_sorts_hard_filter_pass_first(self, mock_qdrant_client, mock_embedding):
        from qdrant_client.models import ScoredPoint

        mock_qdrant_client.scroll.return_value = (
            [MagicMock(id="resume-1", payload={"raw_text": "text", "certs": ["CISSP"], "skills": [], "clearance_level": ""})],
            None,
        )

        mock_qdrant_client.search.return_value = [
            ScoredPoint(id="job-1", version=0, score=0.5, payload={"title": "T1", "company": "C1", "required_certs": ["CEH"], "required_skills": [], "clearance_level": ""}),
            ScoredPoint(id="job-2", version=0, score=0.3, payload={"title": "T2", "company": "C2", "required_certs": ["CISSP"], "required_skills": [], "clearance_level": ""}),
        ]

        results = match_jobs_to_resume("resume-1", top_k=10, min_score=0.0)
        # job-2 should be first (hard_filter_pass=True) even though lower score
        assert results[0].job_id == "job-2"
        assert results[0].hard_filter_pass is True
        assert results[1].job_id == "job-1"
        assert results[1].hard_filter_pass is False
