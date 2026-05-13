"""
Tier 1 — Critical pure-logic tests for dom_mapper.py.
Tests field normalization, matching, and value extraction.
"""
import pytest
from services.automation.dom_mapper import (
    normalize_field_name,
    match_field_to_resume_key,
    extract_value_for_field,
    build_field_mapping,
    FIELD_PATTERNS,
)


class TestNormalizeFieldName:
    def test_lowercase(self):
        assert normalize_field_name("FirstName") == "firstname"

    def test_special_chars_to_dots(self):
        assert normalize_field_name("first_name") == "first.name"
        assert normalize_field_name("first-name") == "first.name"
        assert normalize_field_name("first name") == "first.name"

    def test_multiple_special_chars(self):
        assert normalize_field_name("first__name") == "first..name"

    def test_empty_string(self):
        assert normalize_field_name("") == ""

    def test_numbers_preserved(self):
        assert normalize_field_name("phone1") == "phone1"


class TestMatchFieldToResumeKey:
    def test_first_name_exact(self):
        assert match_field_to_resume_key("first_name") == "first_name"

    def test_first_name_variant(self):
        assert match_field_to_resume_key("firstname") == "first_name"
        assert match_field_to_resume_key("fname") == "first_name"
        assert match_field_to_resume_key("given_name") == "first_name"

    def test_last_name(self):
        assert match_field_to_resume_key("last_name") == "last_name"
        assert match_field_to_resume_key("surname") == "last_name"

    def test_email(self):
        assert match_field_to_resume_key("email") == "email"
        assert match_field_to_resume_key("e-mail") == "email"
        assert match_field_to_resume_key("email_address") == "email"

    def test_phone(self):
        assert match_field_to_resume_key("phone") == "phone"
        assert match_field_to_resume_key("telephone") == "phone"
        assert match_field_to_resume_key("mobile") == "phone"
        assert match_field_to_resume_key("cell") == "phone"

    def test_location(self):
        assert match_field_to_resume_key("location") == "location"
        assert match_field_to_resume_key("city") == "location"

    def test_linkedin(self):
        assert match_field_to_resume_key("linkedin") == "linkedin"
        assert match_field_to_resume_key("linkedin_url") == "linkedin"

    def test_summary(self):
        assert match_field_to_resume_key("summary") == "summary"
        assert match_field_to_resume_key("objective") == "summary"
        assert match_field_to_resume_key("about") == "summary"

    def test_skills(self):
        assert match_field_to_resume_key("skills") == "skills"
        assert match_field_to_resume_key("technical_skills") == "skills"
        assert match_field_to_resume_key("qualifications") == "skills"

    def test_experience(self):
        assert match_field_to_resume_key("experience") == "experience"
        assert match_field_to_resume_key("work_history") == "experience"

    def test_education(self):
        assert match_field_to_resume_key("education") == "education"
        assert match_field_to_resume_key("degree") == "education"
        assert match_field_to_resume_key("university") == "education"

    def test_certifications(self):
        assert match_field_to_resume_key("certifications") == "certifications"
        assert match_field_to_resume_key("licenses") == "certifications"

    def test_resume_upload(self):
        assert match_field_to_resume_key("resume") == "resume_upload"
        assert match_field_to_resume_key("cv") == "resume_upload"
        assert match_field_to_resume_key("upload") == "resume_upload"

    def test_cover_letter_upload(self):
        assert match_field_to_resume_key("cover_letter") == "cover_letter_upload"

    def test_no_match(self):
        assert match_field_to_resume_key("favorite_color") is None
        assert match_field_to_resume_key("xyz123") is None

    def test_empty_string(self):
        assert match_field_to_resume_key("") is None

    @pytest.mark.parametrize("field_name,expected_key", [
        ("first_name", "first_name"),
        ("last_name", "last_name"),
        ("email", "email"),
        ("phone_number", "phone"),
        ("city", "location"),
        ("skills", "skills"),
        ("work_experience", "experience"),
        ("school", "education"),
        ("certificates", "certifications"),
        ("resume_upload", "resume_upload"),
    ])
    def test_parametrized_matches(self, field_name, expected_key):
        assert match_field_to_resume_key(field_name) == expected_key


class TestExtractValueForField:
    @pytest.fixture
    def resume_with_contact(self):
        return {
            "contact_info": {
                "name": "Jane Doe",
                "email": "jane@example.com",
                "phone": "555-0123",
                "location": "Washington, DC",
                "linkedin": "linkedin.com/in/janedoe",
            },
            "tailored_summary": "Experienced cybersecurity professional.",
            "skills_highlighted": ["SIEM", "Splunk", "Python"],
            "certifications_emphasized": ["CISSP", "CEH"],
            "experience": [
                {
                    "title": "Security Analyst",
                    "company": "Tech Corp",
                    "bullets": [
                        {"original": "Managed SIEM", "tailored": "Architected SIEM deployment"},
                    ],
                }
            ],
        }

    def test_first_name(self, resume_with_contact):
        assert extract_value_for_field("first_name", resume_with_contact) == "Jane"

    def test_last_name(self, resume_with_contact):
        assert extract_value_for_field("last_name", resume_with_contact) == "Doe"

    def test_single_word_name(self):
        resume = {"contact_info": {"name": "Madonna"}}
        assert extract_value_for_field("first_name", resume) == "Madonna"
        assert extract_value_for_field("last_name", resume) is None

    def test_email(self, resume_with_contact):
        assert extract_value_for_field("email", resume_with_contact) == "jane@example.com"

    def test_phone(self, resume_with_contact):
        assert extract_value_for_field("phone", resume_with_contact) == "555-0123"

    def test_location(self, resume_with_contact):
        assert extract_value_for_field("location", resume_with_contact) == "Washington, DC"

    def test_linkedin(self, resume_with_contact):
        assert extract_value_for_field("linkedin", resume_with_contact) == "linkedin.com/in/janedoe"

    def test_summary(self, resume_with_contact):
        result = extract_value_for_field("summary", resume_with_contact)
        assert "Experienced cybersecurity professional" in result

    def test_skills(self, resume_with_contact):
        result = extract_value_for_field("skills", resume_with_contact)
        assert "SIEM" in result
        assert "Splunk" in result
        assert "Python" in result

    def test_experience(self, resume_with_contact):
        result = extract_value_for_field("experience", resume_with_contact)
        assert "Security Analyst" in result
        assert "Tech Corp" in result
        assert "Architected SIEM deployment" in result

    def test_certifications(self, resume_with_contact):
        result = extract_value_for_field("certifications", resume_with_contact)
        assert "CISSP" in result
        assert "CEH" in result

    def test_unknown_key(self, resume_with_contact):
        assert extract_value_for_field("nonexistent", resume_with_contact) is None

    def test_missing_contact_info(self):
        resume = {"tailored_summary": "Summary only"}
        assert extract_value_for_field("first_name", resume) is None
        assert extract_value_for_field("email", resume) is None

    def test_empty_name(self):
        resume = {"contact_info": {"name": ""}}
        assert extract_value_for_field("first_name", resume) is None

    def test_empty_skills(self):
        resume = {"skills_highlighted": []}
        assert extract_value_for_field("skills", resume) is None

    def test_empty_certs(self):
        resume = {"certifications_emphasized": []}
        assert extract_value_for_field("certifications", resume) is None


class TestBuildFieldMapping:
    def test_maps_email_field(self):
        from unittest.mock import MagicMock
        mock_page = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.side_effect = lambda attr: {
            "name": "email",
            "id": "email_input",
            "placeholder": "",
            "aria-label": "",
        }.get(attr, "")

        mock_page.query_selector_all.return_value = [mock_element]
        mock_page.query_selector.return_value = None  # No label found

        result = build_field_mapping(mock_page)
        assert "email" in result

    def test_maps_by_placeholder(self):
        from unittest.mock import MagicMock
        mock_page = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.side_effect = lambda attr: {
            "name": "",
            "id": "",
            "placeholder": "Enter your first name",
            "aria-label": "",
        }.get(attr, "")

        mock_page.query_selector_all.return_value = [mock_element]
        mock_page.query_selector.return_value = None

        result = build_field_mapping(mock_page)
        assert "first_name" in result

    def test_no_match_returns_empty(self):
        from unittest.mock import MagicMock
        mock_page = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.side_effect = lambda attr: {
            "name": "favorite_color",
            "id": "color",
            "placeholder": "",
            "aria-label": "",
        }.get(attr, "")

        mock_page.query_selector_all.return_value = [mock_element]
        mock_page.query_selector.return_value = None

        result = build_field_mapping(mock_page)
        assert result == {}

    def test_maps_by_label(self):
        from unittest.mock import MagicMock
        mock_page = MagicMock()
        mock_element = MagicMock()
        mock_element.get_attribute.side_effect = lambda attr: {
            "name": "",
            "id": "phone_input",
            "placeholder": "",
            "aria-label": "",
        }.get(attr, "")

        mock_label = MagicMock()
        mock_label.inner_text.return_value = "Phone Number"

        mock_page.query_selector_all.return_value = [mock_element]
        mock_page.query_selector.return_value = mock_label

        result = build_field_mapping(mock_page)
        assert "phone" in result
