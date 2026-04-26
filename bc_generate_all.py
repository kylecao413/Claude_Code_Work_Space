"""
bc_generate_all.py — Batch generate proposals for all scraped BC projects.
Reads bc_all_projects.json, generates Word + PDF proposals for each.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "bc_all_projects.json"

# Pricing rules
REPEAT_CLIENTS = {"HBW Construction", "PWC Companies"}
REPEAT_PRICE = 325
ONETIME_PRICE = 375

# Visit estimates based on project size and complexity
def estimate_visits(project: dict) -> int:
    """Estimate visits based on size and scope description."""
    size_str = project.get("project_size_sqft", "")
    desc = (project.get("scope_description", "") or "").lower()

    # Parse size
    sqft = 0
    if size_str:
        import re
        m = re.search(r'([\d,]+)', size_str)
        if m:
            sqft = int(m.group(1).replace(",", ""))

    # Base visits on size
    if sqft > 10000:
        visits = 10
    elif sqft > 5000:
        visits = 6
    elif sqft > 2000:
        visits = 4
    elif sqft > 0:
        visits = 3
    else:
        visits = 6  # Default for unknown size

    # Adjust for complexity
    if "generator" in desc or "fire" in desc or "sprinkler" in desc:
        visits += 2
    if "full mep" in desc or "mechanical, electrical" in desc or "hvac" in desc:
        visits += 2
    if "new building" in desc or "new construction" in desc or "two-story" in desc:
        visits += 4
    if "asbestos" in desc:
        visits += 1
    if "roof" in desc and "skylight" in desc:
        visits += 1

    return min(visits, 20)


def get_price(client_short: str) -> int:
    """Get per-visit price based on client."""
    for rc in REPEAT_CLIENTS:
        if rc.lower() in client_short.lower():
            return REPEAT_PRICE
    return ONETIME_PRICE


def main():
    from proposal_generator import run_single_project

    if not INPUT_FILE.exists():
        print(f"Error: {INPUT_FILE} not found. Run bc_scrape_all.py first.", file=sys.stderr)
        sys.exit(1)

    projects = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(projects)} projects from {INPUT_FILE.name}")

    results = []
    for i, proj in enumerate(projects, 1):
        name = proj.get("project_name", proj.get("target_name", f"Project_{i}"))
        client = proj.get("client_short", proj.get("client_name", "Unknown"))
        price = get_price(client)
        visits = estimate_visits(proj)
        total = price * visits

        print(f"\n{'='*60}")
        print(f"[{i}/{len(projects)}] {name}")
        print(f"  GC: {client} | ${price}/visit x {visits} visits = ${total}")
        print(f"  Contact: {proj.get('attention', 'N/A')} <{proj.get('client_email', '')}>")
        print(f"  Address: {proj.get('project_address', 'N/A')}")
        print(f"  Due: {proj.get('bid_due_date', 'N/A')}")

        # Build project dict for proposal_generator
        gen_project = {
            "name": name,
            "client": client,
            "attention": proj.get("attention", ""),
            "contact_name": proj.get("attention", ""),
            "contact_email": proj.get("client_email", ""),
            "address": proj.get("project_address", ""),
            "description": proj.get("scope_description", ""),
        }

        result = run_single_project(
            gen_project,
            price_per_visit=price,
            est_visits=visits,
            skip_confirm=True,
        )

        if result["success"]:
            print(f"  ✓ Word: {result['output_docx']}")
            if result.get("pdf_path"):
                print(f"  ✓ PDF:  {result['pdf_path']}")
            results.append({
                "project": name,
                "client": client,
                "price": price,
                "visits": visits,
                "total": total,
                "docx": result["output_docx"],
                "pdf": result.get("pdf_path", ""),
                "status": "OK",
            })
        else:
            print(f"  ✗ FAILED: {result.get('error', 'unknown')}")
            results.append({
                "project": name,
                "client": client,
                "status": "FAILED",
                "error": result.get("error", ""),
            })

    # Summary
    ok = [r for r in results if r["status"] == "OK"]
    failed = [r for r in results if r["status"] != "OK"]

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {len(ok)} succeeded, {len(failed)} failed")
    print(f"{'='*60}")

    for r in ok:
        print(f"  ✓ {r['project']} | {r['client']} | ${r['price']}x{r['visits']}=${r['total']}")

    for r in failed:
        print(f"  ✗ {r['project']} | {r.get('error', '')}")

    # Save results summary
    summary_path = BASE_DIR / "bc_proposal_results.json"
    summary_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nResults saved to {summary_path.name}")


if __name__ == "__main__":
    main()
