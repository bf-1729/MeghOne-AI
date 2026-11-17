"""Smoke tests: the app boots, serves its home page, and has no JS errors.

Add feature flows next to this file (tests/e2e/test_<feature>.py).
"""

from playwright.sync_api import Page


def test_home_page_loads(page: Page):
    response = page.goto("/")
    assert response is not None, "No response from the app"
    assert response.status < 500, f"Home page returned HTTP {response.status}"


def test_home_page_has_no_js_errors(page: Page):
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto("/")
    page.wait_for_load_state("networkidle")
    assert not errors, f"JavaScript errors on home page: {errors}"
