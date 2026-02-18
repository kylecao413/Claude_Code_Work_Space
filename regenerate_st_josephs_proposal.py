"""
St. Joseph's on Capitol Hill – Phase I: Regenerate proposal from project data (no hardcoding).
Uses project_data/st_josephs_capitol_hill_phase1.json. Exhibit C totals are computed from row visits.
For other projects: add a JSON under project_data/ and run proposal_from_config.py --config that file.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from proposal_from_config import load_project_config, generate_proposal


def main():
    config_path = BASE_DIR / "project_data" / "st_josephs_capitol_hill_phase1.json"
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    out_docx = generate_proposal(config_path)
    print("Proposal saved:", out_docx)
    from proposal_generator import docx_to_pdf
    pdf_path = docx_to_pdf(out_docx)
    if pdf_path:
        print("PDF saved:", pdf_path)
    config = load_project_config(config_path)
    print("\nExhibit C: {} visits × ${}/visit = ${:,}".format(
        config["_est_visits"], config["price_per_visit"], config["_total_fee"]))
    print("Output path:", out_docx.parent.resolve())


if __name__ == "__main__":
    main()
