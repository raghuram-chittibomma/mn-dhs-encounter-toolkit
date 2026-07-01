"""Capture portfolio UI screenshots after real interactions.

Requires: pip install playwright && playwright install chromium
Run Streamlit first: mn-encounter-ui  (or streamlit run ui/app.py)
Then: python scripts/capture_portfolio_screenshots.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "docs" / "images"
EXAMPLES = ROOT / "examples"
BASE_URL = "http://localhost:8501"


def _goto_page(page, name: str) -> None:
    """Select a sidebar navigation item by visible label."""
    sidebar = page.locator('[data-testid="stSidebar"]')
    sidebar.locator('[data-testid="stRadio"] label').filter(has_text=name).click()
    page.wait_for_timeout(800)


def _upload_main_file(page, file_path: Path) -> None:
    """Set the main content area file uploader (not sidebar)."""
    main = page.locator('[data-testid="stMain"]')
    main.locator('input[type="file"]').set_input_files(str(file_path.resolve()))
    page.wait_for_timeout(1200)


def _screenshot(page, filename: str) -> None:
    out = IMAGES / filename
    page.screenshot(path=str(out), full_page=False)
    print(f"Wrote {out.relative_to(ROOT)}")


def capture_validate_837(page) -> None:
    _goto_page(page, "Validate 837")
    _upload_main_file(page, EXAMPLES / "err_missing_umpi.x12")
    page.get_by_text("L3-BILLING-UMPI-REQUIRED", exact=False).wait_for(state="attached", timeout=15_000)
    page.get_by_text("error(s) found", exact=False).wait_for(timeout=5_000)
    page.get_by_text("Findings").scroll_into_view_if_needed()
    _screenshot(page, "validate_837_error_finding.png")


def capture_validation_layers(page) -> None:
    _goto_page(page, "Validation layers")
    page.get_by_role("tab", name="Layer 3").click()
    page.wait_for_timeout(800)
    search = page.get_by_placeholder("e.g. UMPI, L3-BILLING, charge, ISA")
    search.click()
    page.keyboard.type("UMPI", delay=60)
    page.keyboard.press("Enter")
    page.wait_for_timeout(2500)
    page.get_by_text("L3-REFERRING-UMPI-REQUIRED").first.wait_for(state="attached", timeout=15_000)
    page.locator('[data-testid="stMain"]').get_by_text("Search rules").scroll_into_view_if_needed()
    _screenshot(page, "validation_layers_umpi_search.png")


def capture_scenario_lab(page) -> None:
    _goto_page(page, "Scenario lab")
    combo = page.locator('[data-testid="stMain"] [data-baseweb="select"]').first
    combo.click()
    page.wait_for_timeout(500)
    page.locator('[data-baseweb="popover"] li').filter(has_text="clean_professional_original").first.click()
    page.keyboard.press("Escape")
    page.wait_for_timeout(400)
    page.get_by_role("button", name="Generate 837 batch").click()
    page.get_by_text("Generated", exact=False).wait_for(timeout=15_000)
    page.get_by_role("button", name="Download 837 file").wait_for(timeout=5_000)
    _screenshot(page, "scenario_lab_batch_generated.png")


def capture_generate_999(page) -> None:
    _goto_page(page, "Generate 999")
    _upload_main_file(page, EXAMPLES / "clean_batch.x12")
    page.get_by_role("button", name="Generate 999").click()
    page.get_by_text("Generated 999", exact=False).wait_for(timeout=15_000)
    page.get_by_role("button", name="Download 999 file").wait_for(timeout=5_000)
    page.get_by_text("Preview first 40 lines").click()
    page.wait_for_timeout(500)
    _screenshot(page, "generate_999_preview.png")


def main() -> int:
    IMAGES.mkdir(parents=True, exist_ok=True)
    steps = [
        capture_validate_837,
        capture_validation_layers,
        capture_scenario_lab,
        capture_generate_999,
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE_URL, wait_until="networkidle", timeout=30_000)
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=30_000)
        for step in steps:
            print(f"Capturing {step.__name__}...")
            try:
                step(page)
            except PlaywrightTimeout as exc:
                print(f"FAILED {step.__name__}: {exc}", file=sys.stderr)
                browser.close()
                return 1
        browser.close()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
