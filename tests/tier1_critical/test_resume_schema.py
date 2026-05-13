"""
Tier 1 — Critical pure-logic tests for resume/schema.py.
Tests all Pydantic models for structured resume representation.
"""
import pytest
from pydantic import ValidationError
from services.resume.schema import (
    ContactInfo,
    Experience,
    Education,
    Certification,
    ResumeSchema,
    TailoredBullet,
    TailoredExperience,
    TailoredResume,
)


class TestContactInfo:
    def test_defaults(self):
        c = ContactInfo()
        assert c.name == ""
        assert c.email == ""
        assert c.phone == ""
        assert c.location == ""
        assert c.linkedin == ""
        assert c.website == ""

    def test_full_contact(self):
        c = ContactInfo(
            name="Jane Doe",
            email="jane@example.com",
            phone="555-0123",
            location="DC",
            linkedin="linkedin.com/in/jane",
            website="jane.dev",
        )
        assert c.name == "Jane Doe"
        assert c.email == "jane@example.com"

    def test_partial_contact(self):
        c = ContactInfo(name="John", email="john@test.com")
        assert c.name == "John"
        assert c.phone == ""


class TestExperience:
    def test_valid_experience(self):
        exp = Experience(
            title="Security Analyst",
            company="Tech Corp",
            bullets=["Managed SIEM", "Led IR team"],
        )
        assert exp.title == "Security Analyst"
        assert len(exp.bullets) == 2

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            Experience(company="Tech Corp")  # missing title

    def test_defaults(self):
        exp = Experience(title="Engineer", company="Corp")
        assert exp.location == ""
        assert exp.start_date == ""
        assert exp.end_date == ""
        assert exp.bullets == []


class TestEducation:
    def test_valid_education(self):
        edu = Education(degree="BS Computer Science", school="MIT")
        assert edu.degree == "BS Computer Science"
        assert edu.school == "MIT"

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            Education(degree="BS")  # missing school

    def test_defaults(self):
        edu = Education(degree="BS", school="MIT")
        assert edu.graduation_year == ""
        assert edu.gpa == ""


class TestCertification:
    def test_valid_cert(self):
        cert = Certification(name="CISSP", issuer="ISC2", date="2020")
        assert cert.name == "CISSP"
        assert cert.issuer == "ISC2"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            Certification(issuer="ISC2")

    def test_defaults(self):
        cert = Certification(name="CISSP")
        assert cert.issuer == ""
        assert cert.date == ""


class TestResumeSchema:
    def test_empty_resume(self):
        r = ResumeSchema()
        assert r.contact_info.name == ""
        assert r.summary == ""
        assert r.experience == []
        assert r.education == []
        assert r.certifications == []
        assert r.skills == []
        assert r.clearance_level == ""

    def test_full_resume(self):
        r = ResumeSchema(
            contact_info=ContactInfo(name="Jane Doe", email="jane@test.com"),
            summary="Experienced security engineer",
            experience=[
                Experience(title="Security Analyst", company="Tech Corp", bullets=["Did stuff"])
            ],
            education=[Education(degree="BS", school="MIT")],
            certifications=[Certification(name="CISSP")],
            skills=["SIEM", "Python"],
            clearance_level="Top Secret",
        )
        assert r.contact_info.name == "Jane Doe"
        assert len(r.experience) == 1
        assert len(r.skills) == 2
        assert r.clearance_level == "Top Secret"

    def test_wrong_type_raises(self):
        with pytest.raises(ValidationError):
            ResumeSchema(skills="not_a_list")


class TestTailoredBullet:
    def test_valid(self):
        b = TailoredBullet(original="orig", tailored="new")
        assert b.original == "orig"
        assert b.tailored == "new"
        assert b.rationale == ""

    def test_missing_tailored_raises(self):
        with pytest.raises(ValidationError):
            TailoredBullet(original="orig")


class TestTailoredExperience:
    def test_valid(self):
        exp = TailoredExperience(
            title="Engineer",
            company="Corp",
            bullets=[TailoredBullet(original="a", tailored="b")],
        )
        assert len(exp.bullets) == 1

    def test_missing_bullets_raises(self):
        with pytest.raises(ValidationError):
            TailoredExperience(title="Eng", company="Corp")


class TestTailoredResume:
    def test_empty(self):
        tr = TailoredResume()
        assert tr.summary == ""
        assert tr.experience == []
        assert tr.skills_highlighted == []
        assert tr.certifications_emphasized == []
        assert tr.overall_rationale == ""

    def test_full(self):
        tr = TailoredResume(
            summary="Great candidate",
            experience=[
                TailoredExperience(
                    title="Eng", company="Corp",
                    bullets=[TailoredBullet(original="a", tailored="b")],
                )
            ],
            skills_highlighted=["SIEM"],
            certifications_emphasized=["CISSP"],
            overall_rationale="Perfect match",
        )
        assert len(tr.experience) == 1
        assert tr.skills_highlighted == ["SIEM"]
