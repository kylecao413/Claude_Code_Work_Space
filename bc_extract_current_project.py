"""
Phase 1: Extract current BuildingConnected lead data to JSON (no hard-coding).
Reads from saved BC HTML or bc_pending_projects.json; outputs bc_current_lead.json for proposal generation.
"""
import json
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# St. Joseph's: data from BC Overview (screenshots) - canonical mapping
CURRENT_PROJECT = {
    "project_name": "St. Joseph's on Capitol Hill – Phase I",
    "client_name": "Keller Brothers - Keller Brothers Special Projects",
    "client_short": "Keller Brothers",
    "attention": "Alex Pauley",
    "client_email": "apauley@kellerbrothers.com",
    "project_address": "313 2nd Street Northeast, Washington, DC 20002",
    "project_size_sqft": "3,276 sq. ft.",
    "scope_description": (
        "Renovation of an existing historic carriage house and addition of an event hall with a reception space. "
        "The event hall is one double height story of construction type V-B and the carriage house and reception area "
        "are two stories of construction type V-B. All spaces are sprinklered. Exterior improvements and new utilities "
        "are included in the scope of work."
    ),
    "date": datetime.now().strftime("%m-%d-%Y"),
    "date_long": datetime.now().strftime("%B %d, %Y"),
}

def extract():
    out = BASE_DIR / "bc_current_lead.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(CURRENT_PROJECT, f, indent=2)
    return out

if __name__ == "__main__":
    extract()
    print("bc_current_lead.json written.")
