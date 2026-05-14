"""
Live Job Scraper — Playwright-based scraper for job boards.
Targets Indeed, LinkedIn, and Dice with stealth plugins.
"""
import asyncio
from typing import Optional
from loguru import logger

from config.settings import settings


async def _apply_stealth(page) -> None:
    """Apply playwright-stealth to a page if stealth is enabled and available."""
    if not settings.playwright_stealth_enabled:
        return
    try:
        from playwright_stealth import stealth_async
        await stealth_async(page)
    except ImportError:
        logger.debug("playwright-stealth not available — skipping stealth")


async def scrape_indeed(
    query: str = "cybersecurity",
    location: str = "Remote",
    max_jobs: int = 50,
) -> list[dict]:
    """
    Scrape Indeed for cybersecurity job listings.
    Uses Playwright with stealth to avoid detection.
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

            # Wait for job cards to load
            await page.wait_for_selector(".job_seen_beacon, .jobTitle", timeout=10000)

            # Extract job cards
            cards = await page.query_selector_all(".job_seen_beacon, .cardOutline")
            count = 0

            for card in cards[:max_jobs]:
                try:
                    title_el = await card.query_selector(".jobTitle span, h2 a")
                    company_el = await card.query_selector("[data-testid='company-name'], .companyName")
                    location_el = await card.query_selector("[data-testid='text-location'], .companyLocation")

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""

                    if title and company:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "description": f"{title} at {company}",
                            "url": "",
                            "source": "indeed",
                        })
                        count += 1
                except Exception as e:
                    logger.debug(f"Skipping card: {e}")
                    continue

            await browser.close()
            logger.info(f"Indeed: scraped {count} jobs")
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

            cards = await page.query_selector_all(".job-card-container")
            count = 0

            for card in cards[:max_jobs]:
                try:
                    title_el = await card.query_selector(".job-card-list__title")
                    company_el = await card.query_selector(".job-card-container__company-name")
                    location_el = await card.query_selector(".job-card-container__metadata-item")

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""

                    if title and company:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "description": f"{title} at {company}",
                            "url": "",
                            "source": "linkedin",
                        })
                        count += 1
                except Exception:
                    continue

            await browser.close()
            logger.info(f"LinkedIn: scraped {count} jobs")
    except Exception as e:
        logger.error(f"LinkedIn scrape failed: {e}")

    return jobs


async def scrape_dice(
    query: str = "cybersecurity",
    max_jobs: int = 50,
) -> list[dict]:
    """
    Scrape Dice.com for cybersecurity job listings.
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

            cards = await page.query_selector_all(".card, .search-card")
            count = 0

            for card in cards[:max_jobs]:
                try:
                    title_el = await card.query_selector(".card-title-link, h5 a")
                    company_el = await card.query_selector(".company-name, .card-company")
                    location_el = await card.query_selector(".search-result-location, .location")

                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""

                    if title and company:
                        jobs.append({
                            "title": title.strip(),
                            "company": company.strip(),
                            "location": loc.strip(),
                            "description": f"{title} at {company}",
                            "url": "",
                            "source": "dice",
                        })
                        count += 1
                except Exception:
                    continue

            await browser.close()
            logger.info(f"Dice: scraped {count} jobs")
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
