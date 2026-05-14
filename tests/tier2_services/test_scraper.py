"""
Tier 2 — Scraper unit tests.
Tests the _html_to_markdown() conversion helper and _fetch_description_markdown()
async helper. All Playwright calls are mocked — no live browser required.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# _html_to_markdown — pure conversion helper
# ============================================================

class TestHtmlToMarkdown:
    """Tests for the pure _html_to_markdown() helper (no Playwright)."""

    def test_basic_paragraph_conversion(self):
        from services.scraper.scraper import _html_to_markdown
        result = _html_to_markdown("<h1>Senior Engineer</h1><p>Join our team.</p>")
        assert "Senior Engineer" in result
        assert "Join our team" in result

    def test_strips_script_tags(self):
        from services.scraper.scraper import _html_to_markdown
        result = _html_to_markdown("<p>Good content</p><script>alert('xss')</script>")
        assert "Good content" in result
        assert "alert" not in result

    def test_strips_style_tags(self):
        from services.scraper.scraper import _html_to_markdown
        result = _html_to_markdown(
            "<style>.foo { color: red }</style><p>Job description</p>"
        )
        assert "Job description" in result
        assert "color" not in result

    def test_collapses_excess_blank_lines(self):
        from services.scraper.scraper import _html_to_markdown
        result = _html_to_markdown(
            "<p>Line 1</p><p></p><p></p><p></p><p>Line 2</p>"
        )
        assert "\n\n\n" not in result

    def test_truncates_to_max_description_length(self):
        from services.scraper.scraper import _html_to_markdown
        from config.settings import settings
        long_html = "<p>" + ("x" * 60_000) + "</p>"
        result = _html_to_markdown(long_html)
        assert len(result) <= settings.max_description_length

    def test_returns_stripped_string(self):
        from services.scraper.scraper import _html_to_markdown
        result = _html_to_markdown("<p>  Clean text.  </p>")
        assert result == result.strip()

    def test_preserves_unordered_list_items(self):
        from services.scraper.scraper import _html_to_markdown
        result = _html_to_markdown(
            "<ul><li>CISSP required</li><li>Top Secret clearance</li></ul>"
        )
        assert "CISSP" in result
        assert "Top Secret" in result

    def test_empty_html_returns_empty_string(self):
        from services.scraper.scraper import _html_to_markdown
        assert _html_to_markdown("") == ""

    def test_preserves_cert_and_skill_keywords(self):
        from services.scraper.scraper import _html_to_markdown
        html = (
            "<div>"
            "<p>Requirements: CISSP, Top Secret clearance, SIEM experience.</p>"
            "<ul><li>Splunk proficiency</li><li>Incident Response</li></ul>"
            "</div>"
        )
        result = _html_to_markdown(html)
        for kw in ["CISSP", "Top Secret", "SIEM", "Splunk", "Incident Response"]:
            assert kw in result, f"Expected keyword '{kw}' to survive HTML→Markdown"

    def test_heading_style_is_atx(self):
        from services.scraper.scraper import _html_to_markdown
        result = _html_to_markdown("<h2>Requirements</h2>")
        assert "##" in result

    def test_nested_html_converted(self):
        from services.scraper.scraper import _html_to_markdown
        html = (
            "<section>"
            "<h3>About the Role</h3>"
            "<ul><li>OSCP or CISSP preferred</li></ul>"
            "</section>"
        )
        result = _html_to_markdown(html)
        assert "About the Role" in result
        assert "OSCP" in result


# ============================================================
# _fetch_description_markdown — async browser helper
# ============================================================

class TestFetchDescriptionMarkdown:
    """Tests for the async _fetch_description_markdown() helper (mocked Playwright)."""

    @pytest.fixture
    def mock_context_and_page(self):
        """Provides a mock Playwright browser context and a pre-wired page."""
        page = AsyncMock()
        context = MagicMock()
        context.new_page = AsyncMock(return_value=page)
        return context, page

    @pytest.mark.asyncio
    async def test_returns_empty_string_for_empty_url(self, mock_context_and_page):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page
        result = await _fetch_description_markdown(context, "", ["#desc"])
        assert result == ""
        context.new_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_extracts_description_by_matching_selector(
        self, mock_context_and_page
    ):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page

        desc_el = AsyncMock()
        desc_el.inner_html = AsyncMock(
            return_value="<p>CISSP required. Top Secret clearance.</p>"
        )

        async def selector_side_effect(sel):
            return desc_el if sel == "#jobDescriptionText" else None

        page.query_selector = AsyncMock(side_effect=selector_side_effect)

        result = await _fetch_description_markdown(
            context,
            "https://www.indeed.com/job/123",
            ["#jobDescriptionText"],
        )
        assert "CISSP" in result
        assert "Top Secret" in result

    @pytest.mark.asyncio
    async def test_falls_back_to_body_when_selector_not_found(
        self, mock_context_and_page
    ):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page

        body_el = AsyncMock()
        body_el.inner_html = AsyncMock(
            return_value="<body><p>SIEM and Splunk required.</p></body>"
        )

        async def selector_side_effect(sel):
            return body_el if sel == "body" else None

        page.query_selector = AsyncMock(side_effect=selector_side_effect)

        result = await _fetch_description_markdown(
            context, "https://example.com/job", ["#notfound"]
        )
        assert "SIEM" in result
        assert "Splunk" in result

    @pytest.mark.asyncio
    async def test_returns_empty_on_navigation_failure(self, mock_context_and_page):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page
        page.goto = AsyncMock(side_effect=Exception("net::ERR_NAME_NOT_RESOLVED"))

        result = await _fetch_description_markdown(
            context, "https://invalid.example.com/job", ["#desc"]
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_on_timeout(self, mock_context_and_page):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page
        page.goto = AsyncMock(side_effect=Exception("Timeout 15000ms exceeded"))

        result = await _fetch_description_markdown(
            context, "https://slow-site.example.com/job", ["#desc"]
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_page_closed_on_success(self, mock_context_and_page):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page

        el = AsyncMock()
        el.inner_html = AsyncMock(return_value="<p>Job content here.</p>")
        page.query_selector = AsyncMock(return_value=el)

        await _fetch_description_markdown(
            context, "https://example.com/job", ["#desc"]
        )
        page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_page_closed_on_failure(self, mock_context_and_page):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page
        page.goto = AsyncMock(side_effect=RuntimeError("Unexpected crash"))

        await _fetch_description_markdown(
            context, "https://example.com/job", ["#desc"]
        )
        page.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_empty_when_body_also_missing(self, mock_context_and_page):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page
        page.query_selector = AsyncMock(return_value=None)

        result = await _fetch_description_markdown(
            context, "https://example.com/job", ["#desc"]
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_tries_all_selectors_before_fallback(self, mock_context_and_page):
        from services.scraper.scraper import _fetch_description_markdown
        context, page = mock_context_and_page

        second_el = AsyncMock()
        second_el.inner_html = AsyncMock(
            return_value="<p>Found via second selector.</p>"
        )

        call_count = 0

        async def selector_side_effect(sel):
            nonlocal call_count
            call_count += 1
            if sel == ".fallback-selector":
                return second_el
            return None

        page.query_selector = AsyncMock(side_effect=selector_side_effect)

        result = await _fetch_description_markdown(
            context,
            "https://example.com/job",
            ["#first-miss", ".fallback-selector"],
        )
        assert "Found via second selector" in result
        assert call_count >= 2


# ============================================================
# Description pipeline integration: HTML→Markdown→metadata
# ============================================================

class TestDescriptionPipelineIntegration:
    """
    Verifies that job descriptions produced by _html_to_markdown() carry
    the keywords that extract_all_metadata() and the LLM rewriter depend on.
    """

    def test_cert_keywords_survive_conversion(self):
        from services.scraper.scraper import _html_to_markdown
        from services.scraper.metadata_extractor import extract_certs
        html = (
            "<div><h3>Requirements</h3>"
            "<ul>"
            "<li>Active CISSP required</li>"
            "<li>Security+ preferred</li>"
            "<li>OSCP a plus</li>"
            "</ul></div>"
        )
        markdown = _html_to_markdown(html)
        certs = extract_certs(markdown)
        assert "CISSP" in certs
        assert "Security+" in certs
        assert "OSCP" in certs

    def test_clearance_keywords_survive_conversion(self):
        from services.scraper.scraper import _html_to_markdown
        from services.scraper.metadata_extractor import extract_clearance
        html = "<p>Candidates must hold an active TS/SCI clearance.</p>"
        markdown = _html_to_markdown(html)
        clearance = extract_clearance(markdown)
        assert clearance == "Top Secret"

    def test_skill_keywords_survive_conversion(self):
        from services.scraper.scraper import _html_to_markdown
        from services.scraper.metadata_extractor import extract_skills
        html = (
            "<p>Experience with Splunk, SIEM platforms, "
            "Palo Alto firewalls, and Incident Response required.</p>"
        )
        markdown = _html_to_markdown(html)
        skills = extract_skills(markdown)
        assert "Splunk" in skills
        assert "SIEM" in skills
        assert "Palo Alto" in skills
        assert "Incident Response" in skills

    def test_description_is_not_stub_format(self):
        """Guard against regression to the old f'{title} at {company}' stub."""
        from services.scraper.scraper import _html_to_markdown
        real_html = (
            "<div><p>We are seeking a CISSP-certified Cybersecurity Engineer "
            "with Top Secret clearance and Splunk SIEM expertise.</p></div>"
        )
        title, company = "Cybersecurity Engineer", "Acme Corp"
        stub = f"{title} at {company}"
        result = _html_to_markdown(real_html)
        assert result != stub
        assert len(result) > len(stub)
