"""
Fairfax County Third Party Inspections Program — Request & Submission Form auto-filler.

Filed under KCY Engineering Code Consulting, LLC. Opens the public workflowcloud
form, fills Requestor + Project + Inspection fields, selects KCY, optionally
attaches a field report or completion statement, and submits.

Form URL:
  https://fairfaxcounty-639180.workflowcloud.com/forms/c93545e3-4e9d-4984-acaf-2520898fa685

Usage:
  python fairfax_3pi_submit.py \
      --owner-name "Erimiyas Bahiru" \
      --owner-phone "703-346-4525" \
      --owner-email "ermykm@icloud.com" \
      --address "3303 Lockheed Blvd, Alexandria, VA 22306" \
      --permit "ELER-2026-XXXXX" \
      --submission-type request \
      --inspection concealment

For report/completion submittals pass --attachment /path/to/report.pdf.

First run suggestion: add --dry-run to fill but not click Submit, so you can
eyeball the form before it fires.
"""
import argparse
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

FORM_URL = (
    "https://fairfaxcounty-639180.workflowcloud.com/forms/"
    "c93545e3-4e9d-4984-acaf-2520898fa685"
)

TPI_NAME = "KCY Engineering Code Consulting, LLC"
TPI_EMAIL = "ycao@kcyengineer.com"

SUBMISSION_TYPE_LABEL = {
    "request":    "Request to use 3rd Party",
    "report":     "Inspection Report Submittal",
    "completion": "Certified Completion Statement Submittal",
}

INSPECTION_LABEL_MAP = {
    "concealment":  "Building, Mechanical, Electrical, and Plumbing Concealments",
    "final":        "Building, Mechanical, Electrical, and Plumbing Final",
    "basement":     "Concrete basement slabs",
    "electrode":    "Concrete encased electrode (20' min)",
    "cipp":         "Cured in Place Pipe Liner (CIPP) Installations",
    "electemp":    "Electrical temp for perm and temp on pole",
    "footing":      "Foundation footings and walls",
    "helical":      "Helical Piers",
    "mech-insul":   "Mechanical Insulation",
    "pier-ftg":     "Pier footings",
    "concrete":     "Placement of concrete",
    "plumb-ug":     "Plumbing groundworks",
    "post-pour":    "Post-pour Concrete Inspection",
    "stoop":        "Stoop inspections",
    "garage":       "Structural garage slabs",
    "waterproof":   ("Waterproofing or Damp-proofing and backfill of "
                     "concrete foundation walls"),
}


def _fill_by_label(page, label: str, value: str) -> None:
    """Fill a form field whose visible label matches `label`."""
    page.get_by_label(label, exact=False).first.fill(value)


def _check_by_label(page, label: str) -> None:
    """Check a radio/checkbox whose visible label matches `label`.

    Workflowcloud wraps inputs in <label> elements that intercept pointer
    events, so a direct .check() on the input times out. Click the <label>
    via its data-e2e="set-...-<label>" attribute instead.
    """
    safe = label.replace('"', '\\"')
    label_locator = page.locator(f'label[data-e2e$="-{safe}"]').first
    label_locator.scroll_into_view_if_needed()
    label_locator.click()


def _select_tpi(page) -> None:
    """Select KCY Engineering in the Third Party Inspector dropdown.

    Workflowcloud uses custom dropdowns, not native <select>. Try native first,
    then fall back to click-then-option-click.
    """
    dropdown = page.get_by_label("Third Party Inspector", exact=False).first
    try:
        dropdown.select_option(label=TPI_NAME)
        return
    except Exception:
        pass
    dropdown.click()
    page.get_by_text(TPI_NAME, exact=True).first.click()


def submit_form(
    owner_name: str,
    owner_phone: str,
    owner_email: str,
    address: str,
    permit: str,
    submission_type: str,
    inspection: list[str],
    attachment: str | None,
    headless: bool,
    dry_run: bool,
) -> int:
    submission_label = SUBMISSION_TYPE_LABEL[submission_type]
    inspection_labels = [INSPECTION_LABEL_MAP[i] for i in inspection]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        print(f"[1/8] Opening form: {FORM_URL}")
        page.goto(FORM_URL, wait_until="networkidle", timeout=60000)

        print(f"[2/8] Requestor: {owner_name} / {owner_phone} / {owner_email}")
        _fill_by_label(page, "Requestor's Name", owner_name)
        _fill_by_label(page, "Requestor's Phone Number", owner_phone)
        _fill_by_label(page, "Requestor's Email Address", owner_email)

        print(f"[3/8] Project: {address}")
        _fill_by_label(page, "Project Street Address", address)
        print(f"[4/8] Permit: {permit}")
        _fill_by_label(page, "Building Permit Number", permit)

        print(f"[5/8] Submission type: {submission_label}")
        _check_by_label(page, submission_label)

        print(f"[6/8] Inspection types: {inspection_labels}")
        for lbl in inspection_labels:
            _check_by_label(page, lbl)

        print(f"[7/8] Selecting TPI: {TPI_NAME}")
        _select_tpi(page)
        _fill_by_label(page, "Third Party Inspector Email", TPI_EMAIL)

        if attachment:
            print(f"      Attaching: {attachment}")
            file_input = page.locator("input[type='file']").first
            file_input.set_input_files(attachment)
            page.wait_for_timeout(3000)

        if dry_run:
            print("[8/8] DRY RUN — not clicking Submit. Inspect the browser.")
            print("      Close the window manually when done.")
            while not page.is_closed():
                time.sleep(1)
            browser.close()
            return 0

        print("[8/8] Clicking Submit")
        page.get_by_role("button", name="Submit").click()

        # Wait for the server confirmation — workflowcloud shows either a
        # success message or redirects. networkidle alone fires too early
        # (before the server response returns), so look for text instead.
        confirmation_patterns = [
            "text=/thank you/i",
            "text=/submitted/i",
            "text=/received/i",
            "text=/success/i",
        ]
        confirmed = False
        for sel in confirmation_patterns:
            try:
                page.wait_for_selector(sel, timeout=20000)
                confirmed = True
                break
            except PwTimeout:
                continue
        if not confirmed:
            # Final fallback: wait for networkidle + small delay
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except PwTimeout:
                pass
            page.wait_for_timeout(3000)

        out_dir = Path(__file__).resolve().parent
        screenshot = out_dir / f"fairfax_submit_{permit}_{submission_type}.png"
        page.screenshot(path=str(screenshot), full_page=True)
        status = "confirmed" if confirmed else "submitted (no confirmation text matched — verify email)"
        print(f"[OK] {status}. Screenshot: {screenshot}")

        browser.close()
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--owner-name", required=True)
    ap.add_argument("--owner-phone", required=True)
    ap.add_argument("--owner-email", required=True)
    ap.add_argument("--address", required=True, help="Project street address")
    ap.add_argument("--permit", required=True, help="Building Permit # (ALTR/MECHR/ELER/PLMR-YYYY-XXXXX)")
    ap.add_argument("--submission-type", required=True,
                    choices=list(SUBMISSION_TYPE_LABEL))
    ap.add_argument("--inspection", required=True, nargs="+",
                    choices=list(INSPECTION_LABEL_MAP))
    ap.add_argument("--attachment",
                    help="PDF path — required for submission-type report/completion")
    ap.add_argument("--headless", action="store_true",
                    help="Run without visible browser (default: headed)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Fill the form but do NOT click Submit")
    args = ap.parse_args()

    if args.submission_type in ("report", "completion") and not args.attachment:
        print(f"ERROR: --attachment required for submission-type={args.submission_type}",
              file=sys.stderr)
        return 2
    if args.attachment and not Path(args.attachment).exists():
        print(f"ERROR: attachment not found: {args.attachment}", file=sys.stderr)
        return 2

    return submit_form(
        owner_name=args.owner_name,
        owner_phone=args.owner_phone,
        owner_email=args.owner_email,
        address=args.address,
        permit=args.permit,
        submission_type=args.submission_type,
        inspection=args.inspection,
        attachment=args.attachment,
        headless=args.headless,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
