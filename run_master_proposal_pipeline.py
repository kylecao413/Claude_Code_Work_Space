"""
MASTER PROTOCOL: Autonomous Proposal Generation & QA Pipeline.
Phase 1: Extract BC data -> Phase 2: Generate + Internal Audit loop -> Phase 3: Hand-off.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_NAME = "St. Joseph's on Capitol Hill – Phase I"
OUT_DOCX = Path(r"c:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Keller Brothers\St. Joseph's on Capitol Hill – Phase I\St. Joseph's on Capitol Hill – Phase I - Third Party Code Inspection Proposal from BCC.docx")
REAL_CLIENT = "Keller Brothers"
REAL_ADDRESS = "313 2nd Street Northeast, Washington, DC 20002"

def phase1_extract():
    sys.path.insert(0, str(BASE_DIR))
    from bc_extract_current_project import extract
    extract()
    print("[Phase 1] BC data extracted to bc_current_lead.json")


def phase2_generate_and_audit(max_loops=3):
    sys.path.insert(0, str(BASE_DIR))
    from internal_audit_proposal import audit
    for attempt in range(max_loops):
        # Generate
        import subprocess
        r = subprocess.run(
            [sys.executable, str(BASE_DIR / "regenerate_st_josephs_proposal.py")],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            print("[Phase 2] Generate failed:", r.stderr or r.stdout)
            continue
        if not OUT_DOCX.exists():
            alt = OUT_DOCX.parent / (OUT_DOCX.stem + " - CORRECTED.docx")
            path = alt if alt.exists() else OUT_DOCX
        else:
            path = OUT_DOCX
        if audit(path):
            return True
    return False


def main():
    phase1_extract()
    if not phase2_generate_and_audit():
        print("Pipeline stopped: Internal Audit did not pass after retries.", file=sys.stderr)
        sys.exit(1)
    # Phase 3 (Gemini web verification) removed — internal audit is the QA gate.
    # Phase 3: hand-off
    out_dir = OUT_DOCX.parent
    print()
    print("=" * 60)
    print(f"Proposal for {PROJECT_NAME} generated and audited.")
    print("Ready for your final review in:")
    print(f"  {out_dir}")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    main()
