"""
Live Job Scraper — Playwright-based scraper for job boards.
Targets Indeed, LinkedIn, and Dice with stealth plugins.

Two-pass design per source:
  Pass 1 — navigate the search results page and collect card metadata
            (title / company / location / URL).
  Pass 2 — concurrently fetch each job's detail page, extract the full
            HTML description, and convert it to clean Markdown using
            BeautifulSoup + markdownify.
"""
import asyncio
import re
from typing import Optional
from loguru import logger

from config.settings import settings


# ── Board-specific description selectors (tried in order; <body> fallback) ──
_INDEED_DESC_SELECTORS = [
    "#jobDescriptionText",
    ".jobsearch-JobComponent-description",
]
_LINKEDIN_DESC_SELECTORS = [
    ".description__text",
    ".jobs-description__content",
]
_DICE_DESC_SELECTORS = [
    '[data-cy="jobDescriptionHtml"]',
    "#jobdescSec",
    ".job-description",
]


async def _apply_stealth(page) -> None:
    """Apply playwright-stealth to a page if stealth is enabled and available."""
    if not settings.playwright_stealth_enabled:
        return
    try:
        from playwright_stealth import Stealth
        await Stealth().apply_stealth_async(page)
    except ImportError:
        logger.debug("playwright-stealth not available — skipping stealth")


def _html_to_markdown(html: str) -> str:
    """
    Convert a raw HTML string to clean ATX-style Markdown.
    Removes <script> and <style> elements and their content via BeautifulSoup
    before conversion (markdownify's strip= keeps tag content; decompose does
    not). Collapses runs of 3+ blank lines and truncates to
    settings.max_description_length.
    """
    if not html:
        return ""
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()
    markdown = md(str(soup), heading_style="ATX")
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return markdown[: settings.max_description_length]


async def _fetch_description_markdown(
    context,
    url: str,
    selectors: list[str],
) -> str:
    """
    Open a new tab in the existing browser context, navigate to the job detail
    URL, extract the description HTML using board-specific selectors (falls back
    to <body>), and return clean Markdown. Returns "" on any failure — never
    raises.
    """
    if not url:
        return ""
    page = None
    try:
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)

        html = ""
        for selector in selectors:
            el = await page.query_selector(selector)
            if el:
                html = await el.inner_html()
                break

        if not html:
            body = await page.query_selector("body")
            html = await body.inner_html() if body else ""

        return _html_to_markdown(html)
    except Exception as e:
        logger.debug(f"Description fetch failed for {url}: {e}")
        return ""
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


async def scrape_indeed(
    query: str = "cybersecurity",
    location: str = "Remote",
    max_jobs: int = 50,
) -> list[dict]:
    """
    Scrape Indeed for cybersecurity job listings.
    Pass 1: collect job cards (title / company / location / URL).
    Pass 2: concurrently fetch full job descriptions from detail pages.
    """
    from playwright.async_api import async_playwright

    jobs = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.playwright_headless)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            await _apply_stealth(page)

            search_url = (
                f"https://www.indeed.com/jobs?q={query}&l={location}&filter=0"
            )
            logger.info(f"Scraping Indeed: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(".job_seen_beacon, .jobTitle", timeout=10000)

            # Pass 1: collect card metadata including job URLs
            cards = await page.query_selector_all(".job_seen_beacon, .cardOutline")
            for card in cards[:max_jobs]:
                try:
                    title_el = await card.query_selector(".jobTitle span, h2 a")
                    company_el = await card.query_selector(
                        "[data-testid='company-name'], .companyName"
                    )
                    location_el = await card.query_selector(
                        "[data-testid='text-location'], .companyLocation"
                    )
                    link_el = await card.query_selector(".jobTitle a, h2 a")

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""
                    url = (
                        f"https://www.indeed.com{href}"
                        if href and href.startswith("/")
                        else href or ""
                    )

                    if title and company:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "description": "",
                            "url": url,
                            "source": "indeed",
                        })
                except Exception as e:
                    logger.debug(f"Skipping card: {e}")

            # Pass 2: concurrently fetch full descriptions
            if jobs:
                descriptions = await asyncio.gather(*[
                    _fetch_description_markdown(
                        context, job["url"], _INDEED_DESC_SELECTORS
                    )
                    for job in jobs
                ])
                for job, desc in zip(jobs, descriptions):
                    job["description"] = desc

            await browser.close()
            logger.info(f"Indeed: scraped {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"Indeed scrape failed: {e}")

    return jobs


async def scrape_linkedin(
    query: str = "cybersecurity engineer",
    max_jobs: int = 50,
) -> list[dict]:
    """
    Scrape LinkedIn for cybersecurity job listings.
    Note: LinkedIn aggressively blocks scrapers. Use with caution.
    Pass 1: collect job cards (title / company / location / URL).
    Pass 2: concurrently fetch full job descriptions from detail pages.
    """
    from playwright.async_api import async_playwright

    jobs = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.playwright_headless)
            context = await browser.new_context()
            page = await context.new_page()
            await _apply_stealth(page)

            search_url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={query}&location=United%20States&f_WT=2"
            )
            logger.info(f"Scraping LinkedIn: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(".job-card-container", timeout=10000)

            # Pass 1: collect card metadata including job URLs
            cards = await page.query_selector_all(".job-card-container")
            for card in cards[:max_jobs]:
                try:
                    title_el = await card.query_selector(".job-card-list__title")
                    company_el = await card.query_selector(
                        ".job-card-container__company-name"
                    )
                    location_el = await card.query_selector(
                        ".job-card-container__metadata-item"
                    )

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""
                    href = (
                        await title_el.get_attribute("href") if title_el else ""
                    )
                    url = href or ""

                    if title and company:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "description": "",
                            "url": url,
                            "source": "linkedin",
                        })
                except Exception:
                    continue

            # Pass 2: concurrently fetch full descriptions
            if jobs:
                descriptions = await asyncio.gather(*[
                    _fetch_description_markdown(
                        context, job["url"], _LINKEDIN_DESC_SELECTORS
                    )
                    for job in jobs
                ])
                for job, desc in zip(jobs, descriptions):
                    job["description"] = desc

            await browser.close()
            logger.info(f"LinkedIn: scraped {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"LinkedIn scrape failed: {e}")

    return jobs


async def scrape_dice(
    query: str = "cybersecurity",
    max_jobs: int = 50,
) -> list[dict]:
    """
    Scrape Dice.com for cybersecurity job listings.
    Pass 1: collect job cards (title / company / location / URL).
    Pass 2: concurrently fetch full job descriptions from detail pages.
    """
    from playwright.async_api import async_playwright

    jobs = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.playwright_headless)
            context = await browser.new_context()
            page = await context.new_page()
            await _apply_stealth(page)

            search_url = f"https://www.dice.com/jobs?q={query}&countryCode=US"
            logger.info(f"Scraping Dice: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector(".card, .search-card", timeout=10000)

            # Pass 1: collect card metadata including job URLs
            cards = await page.query_selector_all(".card, .search-card")
            for card in cards[:max_jobs]:
                try:
                    title_el = await card.query_selector(".card-title-link, h5 a")
                    company_el = await card.query_selector(
                        ".company-name, .card-company"
                    )
                    location_el = await card.query_selector(
                        ".search-result-location, .location"
                    )

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""
                    href = (
                        await title_el.get_attribute("href") if title_el else ""
                    )
                    url = (
                        f"https://www.dice.com{href}"
                        if href and href.startswith("/")
                        else href or ""
                    )

                    if title and company:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "description": "",
                            "url": url,
                            "source": "dice",
                        })
                except Exception:
                    continue

            # Pass 2: concurrently fetch full descriptions
            if jobs:
                descriptions = await asyncio.gather(*[
                    _fetch_description_markdown(
                        context, job["url"], _DICE_DESC_SELECTORS
                    )
                    for job in jobs
                ])
                for job, desc in zip(jobs, descriptions):
                    job["description"] = desc

            await browser.close()
            logger.info(f"Dice: scraped {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"Dice scrape failed: {e}")

    return jobs


async def run_all_scrapers(max_per_source: Optional[int] = None) -> list[dict]:
    """Run all configured scrapers and aggregate results."""
    if max_per_source is None:
        max_per_source = settings.scraper_max_jobs_per_source

    sources = [s.strip() for s in settings.scraper_sources.split(",")]
    all_jobs: list[dict] = []

    tasks = []
    if "indeed" in sources:
        tasks.append(scrape_indeed(max_jobs=max_per_source))
    if "linkedin" in sources:
        tasks.append(scrape_linkedin(max_jobs=max_per_source))
    if "dice" in sources:
        tasks.append(scrape_dice(max_jobs=max_per_source))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)
        elif isinstance(result, Exception):
            logger.error(f"Scraper error: {result}")

    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs


def scrape_sync() -> list[dict]:
    """Synchronous wrapper for Celery tasks."""
    return asyncio.run(run_all_scrapers())
