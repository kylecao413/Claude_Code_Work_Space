#!/usr/bin/env bash
# Download all enumerated Fairfax plan-review PDFs into the right subfolders.
# Idempotent: skips files that already exist with non-zero size.
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1

DL() {
  local dest="$1"
  local url="$2"
  local dir
  dir="$(dirname "$dest")"
  mkdir -p "$dir"
  if [[ -s "$dest" ]]; then
    echo "  SKIP $dest"
    return 0
  fi
  echo "  GET  $dest"
  curl -sL -o "$dest" "$url" || { echo "  FAIL $url"; return 1; }
  if [[ ! -s "$dest" ]]; then
    echo "  EMPTY $dest"
    rm -f "$dest"
    return 1
  fi
}

echo "=== Plan Review Records ==="
DL "Plan_Review_Records/2018/Electrical/electrical-plan-review-record-2018.pdf"          "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/forms/electrical-plan-review-record-2018.pdf"
DL "Plan_Review_Records/2018/Interior_Alterations/interior-alterations-plan-review-record-2018.pdf" "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/forms/interior-alterations-plan-review-record-2018.pdf"
DL "Plan_Review_Records/2018/New_Commercial_Building/new-commercial-building-plan-review-record-2018.pdf" "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/forms/new-commercial-building-plan-review-record-2018.pdf"
DL "Plan_Review_Records/2018/Fire_Plan_Review/fire-plan-review-record-2018.pdf"          "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/assets/documents/pdf/fire%20marshal/fire-plan-review-record-2018.pdf"
DL "Plan_Review_Records/2018/Mechanical/mechanical-plan-review-record-2018.pdf"          "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/forms/mechanical-plan-review-record-2018.pdf"
DL "Plan_Review_Records/2018/Plumbing_Gas/plumbing-gas-plan-review-record-2018.pdf"      "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/forms/plumbing-gas-plan-review-record-2018.pdf"

DL "Plan_Review_Records/2021/Electrical/electrical-plan-review-record-2020.pdf"          "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/pdf/forms/electrical-plan-review-record-2020.pdf"
DL "Plan_Review_Records/2021/Interior_Alterations/interior-alterations-plan-review-record-2021.pdf" "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/pdf/forms/interior-alterations-plan-review-record-2021.pdf"
DL "Plan_Review_Records/2021/New_Commercial_Building/new-commercial-building-plan-review-record-2021.pdf" "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/pdf/forms/new-commercial-building-plan-review-record-2021.pdf"
DL "Plan_Review_Records/2021/Fire_Plan_Review/fire-plan-review-record-2021.pdf"          "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/pdf/forms/fire-plan-review-record-2021.pdf"
DL "Plan_Review_Records/2021/Mechanical/mechanical-plan-review-record-2021.pdf"          "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/pdf/forms/mechanical-plan-review-record-2021.pdf"
DL "Plan_Review_Records/2021/Plumbing_Gas/plumbing-gas-plan-review-record-2021.pdf"      "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/pdf/forms/plumbing-gas-plan-review-record-2021.pdf"

echo "=== Common Rejection Reasons ==="
DL "Common_Rejection_Reasons/Building/rej_building_commercial.pdf"        "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/development-process/rej_building.pdf"
DL "Common_Rejection_Reasons/Building/rej_residential.pdf"                "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/development-process/rej_residential.pdf"
DL "Common_Rejection_Reasons/Electrical/rej_electrical.pdf"               "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/development-process/rej_electrical.pdf"
DL "Common_Rejection_Reasons/Mechanical/rej_mechanical.pdf"               "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/development-process/rej_mechanical.pdf"
DL "Common_Rejection_Reasons/Plumbing_Gas/rej_plumbing.pdf"               "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/development-process/rej_plumbing.pdf"
DL "Common_Rejection_Reasons/Fire_Protection/2018_plan_review_comments.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/assets/documents/pdf/fire%20marshal/2018%20plan%20review%20comments.pdf"
DL "Common_Rejection_Reasons/Fire_Protection/2021_plan_review_comments.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/Assets/Documents/PDF/fire%20marshal/2021%20plan%20review%20comments.pdf"

echo "=== Submission Resources — Smoke Control ==="
DL "Submission_Resources/Smoke_Control/smoke_control_VCC_2021_manual.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/Assets/Documents/PDF/fire%20marshal/smoke%20control%20VCC%202021.pdf"
DL "Submission_Resources/Smoke_Control/smoke_control_VCC_2018_manual.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/Assets/Documents/PDF/Fire%20Marshal/smoke%20control%20VCC%202018.pdf"
DL "Submission_Resources/Smoke_Control/smoke_control_VCC_2015_manual.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/assets/documents/pdf/fire%20marshal/smoke%20control%20final%20vcc%202015.pdf"
DL "Submission_Resources/Smoke_Control/smoke_control_supplemental_checklist.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/assets/documents/pdf/fire%20marshal/smoke%20control%20supplemental%20checklist.pdf"
DL "Submission_Resources/Smoke_Control/smoke_control_PLUS_guidelines.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/Assets/Documents/PDF/fire%20marshal/Smoke%20Control%20PLUS%20Guidelines.pdf"

echo "=== Submission Resources — Building (coversheet) ==="
DL "Submission_Resources/Building/building-plan-review-cover-sheet.pdf"   "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/Documents/forms/building-plan-review-cover-sheet.pdf"

echo "=== Submission Resources — Structural (Special Inspections) ==="
DL "Submission_Resources/Structural/2021-special-inspections-program.pdf" "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/publications/2021-special-inspections-program.pdf"
DL "Submission_Resources/Structural/2018-special-inspections-program.pdf" "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/publications/2018-special-inspections-program.pdf"
DL "Submission_Resources/Structural/sip-final-report.doc"                 "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/publications/sip-final-report.doc"
DL "Submission_Resources/Structural/sip-stripping-letter.doc"             "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/publications/sip-stripping-letter.doc"
DL "Submission_Resources/Structural/sip-temperature-log.doc"              "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/documents/PDF/publications/sip-temperature-log.doc"

echo "=== Other Agency Reviews — Fire Marshal Commercial ==="
DL "Other_Agency_Reviews/Fire_Marshal_Commercial/fire_marshal_commercial_plan_review_submittal_requirements.pdf" "https://www.fairfaxcounty.gov/fire-ems/sites/fire-ems/files/assets/documents/pdf/fire%20marshal/fire%20marshal%20commercial%20plan%20review%20submittal%20requirements.pdf"

echo "=== County Details ==="
DL "County_Details/Decks/deck-details.pdf"                               "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/assets/documents/pdf/publications/deck-details.pdf"
DL "County_Details/Finished_Basements/basement-details.pdf"              "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/Documents/PDF/publications/basement-details.pdf"
DL "County_Details/Carport_Enclosures/carport_details.pdf"               "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/Documents/PDF/publications/carport_details.pdf"
DL "County_Details/Retaining_Walls/retaining-wall-details.pdf"           "https://www.fairfaxcounty.gov/landdevelopment/sites/landdevelopment/files/Assets/Documents/PDF/publications/retaining-wall-details.pdf"

echo ""
echo "=== Done. Verifying file sizes ==="
find . -name "*.pdf" -o -name "*.doc" | while read f; do
  sz=$(stat -c%s "$f" 2>/dev/null || stat -f%z "$f" 2>/dev/null)
  printf "%10s  %s\n" "$sz" "$f"
done
