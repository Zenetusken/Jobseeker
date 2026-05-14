"""
Playwright Submitter — Headless browser automation for job applications.
Navigates application portals, fills forms, uploads resumes, and submits.
"""
import os
import datetime
from typing import Optional
from loguru import logger

from config.settings import settings
from services.automation.dom_mapper import build_field_mapping, extract_value_for_field
from services.automation.pdf_generator import generate_tailored_resume_pdf


def _apply_stealth_sync(page) -> None:
    """Apply playwright-stealth to a sync page if enabled and available."""
    if not settings.playwright_stealth_enabled:
        return
    try:
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(page)
    except ImportError:
        logger.debug("playwright-stealth not available — skipping stealth")


def submit_application(
    job_url: str,
    tailored_resume: dict,
    job_id: str,
    output_dir: str = "/app/data/outputs",
) -> dict:
    """
    Submit a tailored resume to a job application portal using Playwright.
    
    Steps:
    1. Generate PDF of tailored resume
    2. Launch headless browser
    3. Navigate to application URL
    4. Map and fill form fields
    5. Upload resume PDF
    6. Submit and capture confirmation
    """
    from playwright.sync_api import sync_playwright

    result = {
        "status": "pending",
        "job_id": job_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "screenshot": None,
        "error": None,
    }

    os.makedirs(output_dir, exist_ok=True)

    # Generate PDF
    pdf_path = os.path.join(output_dir, f"tailored_resume_{job_id}.pdf")
    try:
        generate_tailored_resume_pdf(tailored_resume, pdf_path)
        logger.info(f"Resume PDF generated: {pdf_path}")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        result["status"] = "failed"
        result["error"] = f"PDF generation: {e}"
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=settings.playwright_headless,
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
            )
            page = context.new_page()
            _apply_stealth_sync(page)

            # Navigate to application URL
            logger.info(f"Navigating to: {job_url}")
            page.goto(job_url, wait_until="domcontentloaded", timeout=settings.playwright_timeout_ms)

            # Wait for form to be present
            page.wait_for_load_state("networkidle", timeout=10000)

            # Build field mapping
            logger.info("Mapping form fields...")
            field_mapping = build_field_mapping(page)

            # Fill mapped fields
            for resume_key, selector in field_mapping.items():
                value = extract_value_for_field(resume_key, tailored_resume)
                if value:
                    try:
                        el = page.query_selector(selector)
                        if el:
                            tag = el.evaluate("el => el.tagName.toLowerCase()")
                            if tag == "select":
                                el.select_option(label=value)
                            else:
                                el.fill(value)
                            logger.debug(f"Filled {resume_key}: {value[:50]}...")
                    except Exception as e:
                        logger.warning(f"Could not fill {resume_key}: {e}")

            # Upload resume PDF
            file_inputs = page.query_selector_all("input[type='file']")
            for fi in file_inputs:
                try:
                    fi.set_input_files(pdf_path)
                    logger.info(f"Uploaded resume PDF to file input")
                    break
                except Exception as e:
                    logger.warning(f"File upload failed: {e}")

            # Take pre-submit screenshot
            screenshot_path = os.path.join(output_dir, f"pre_submit_{job_id}.png")
            page.screenshot(path=screenshot_path, full_page=True)
            result["screenshot"] = screenshot_path

            # Find and click submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Submit')",
                "button:has-text('Apply')",
                "a:has-text('Submit')",
                ".submit-button",
                "#submit",
            ]

            submitted = False
            for sel in submit_selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        logger.info(f"Clicking submit: {sel}")
                        btn.click()
                        submitted = True
                        break
                except Exception:
                    continue

            if submitted:
                # Wait for confirmation
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(3000)

                # Take confirmation screenshot
                confirm_path = os.path.join(output_dir, f"confirm_{job_id}.png")
                page.screenshot(path=confirm_path, full_page=True)

                result["status"] = "submitted"
                result["screenshot"] = confirm_path
                logger.info(f"Application submitted: {job_id}")
            else:
                result["status"] = "form_filled_no_submit"
                result["error"] = "Could not find submit button"
                logger.warning(f"No submit button found for {job_id}")

            browser.close()

    except Exception as e:
        logger.error(f"Submission error: {e}")
        result["status"] = "failed"
        result["error"] = str(e)

    return result
