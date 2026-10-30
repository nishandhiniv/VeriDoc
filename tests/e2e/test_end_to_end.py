"""SM-1 end-to-end in a real browser: submit → report → queue → decision.

Runs against a live server:  E2E_BASE_URL=http://127.0.0.1:8770 E2E_REVIEWER_PASSWORD=… python -m pytest tests/e2e
Skipped when E2E_BASE_URL is not set.
"""
import os
import re
from pathlib import Path

import pytest

BASE = os.environ.get("E2E_BASE_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="set E2E_BASE_URL to run browser tests")
SAMPLES = Path(__file__).resolve().parents[2] / "samples"


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def read_sample_marks():
    text = (SAMPLES / "README.md").read_text()
    block = text.split("tn_hsc_marksheet.png")[1].split("##")[0]
    return re.findall(r"\| ([A-Za-z ]+?) \| (\d+) \|", block)


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 900}, {"width": 375, "height": 800}])
def test_full_flow(browser, viewport):
    page = browser.new_page(viewport=viewport)
    page.set_default_timeout(120_000)  # validation may take a while on a sleeping free server
    page.goto(BASE + "/")
    page.click("text=Start application")

    marks = read_sample_marks()
    page.fill("#full_name", "E2E Test Candidate")
    page.fill("#date_of_birth", "2006-04-17")
    page.fill("#contact", "e2e@example.com")
    page.select_option("#board", "tn_hsc")
    page.fill("#register_number", "5276063")
    for i, (subject, mark) in enumerate(marks):
        page.select_option(f"#subject_{i}", subject)
        # Plant one wrong mark: the system must flag it.
        page.fill(f"#mark_{i}", str(int(mark) - 4) if i == 1 else mark)
    page.click("text=Continue to documents")

    page.set_input_files("#marksheet", str(SAMPLES / "tn_hsc_marksheet.png"))
    page.set_input_files("#photo", str(SAMPLES / "photo_valid.jpg"))
    page.click("text=Continue to check and submit")
    assert page.locator("#review-marks").is_visible()
    page.click("#submit-btn")
    page.wait_for_url("**/apply/submitted")
    reference = page.inner_text("#reference").strip()
    assert re.fullmatch(r"VD-\d{4}-\d{5}", reference)

    page.goto(BASE + "/staff/login")
    page.fill("#email", os.environ.get("E2E_REVIEWER_EMAIL", "reviewer@veridoc.test"))
    page.fill("#password", os.environ["E2E_REVIEWER_PASSWORD"])
    page.click("form.sheet button[type=submit]")
    page.wait_for_url("**/staff/")
    assert reference in page.inner_text("#queue")

    page.click(f"text={reference}")
    wrong_subject, right = marks[1]
    row = page.locator("#checks-marks tr", has_text=f"{wrong_subject} marks")
    assert "Mismatch" in row.inner_text()
    assert f"Entered: {int(right) - 4}, Uploaded: {right}" in row.inner_text()
    assert "Needs review" in page.inner_text("#overall-status")

    page.check("input[value=reupload]")
    page.fill("#comment", f"{wrong_subject}: please check your entered mark.")
    page.click("text=Record decision")
    page.wait_for_url("**/staff/")
    page.goto(BASE + "/staff/?status=decided")
    assert reference in page.inner_text("#queue")
    page.close()
