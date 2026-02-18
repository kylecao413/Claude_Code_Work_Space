# Project proposal data (data-driven, no hardcoding)

Each proposal is driven by a **JSON config**. The script never hardcodes client, address, or Exhibit C totals; it **computes** total visits and total fee from the row data so you don't get 1+1+1+1 ≠ 9 again.

## Add a new proposal

1. Copy `st_josephs_capitol_hill_phase1.json` to a new file, e.g. `project_data/my_new_project.json`.
2. Edit the JSON:
   - `client_full`, `client_short`, `attention`, `client_email`
   - `project_name`, `project_address`, `project_size_sqft`
   - `exhibit_a_scope_only` (short scope text; full paragraph is built with address + BCC role)
   - `price_per_visit`
   - `exhibit_c_rows`: list of `{ "keyword": "underground", "visits": 2 }` etc.  
     The **keyword** must appear in the first column (Services) of that row in the template so we can match.  
     **visits** per row; total visits and total fee are computed automatically.
3. Run:
   ```bash
   python proposal_from_config.py project_data/my_new_project.json
   ```
   or
   ```bash
   python proposal_from_config.py my_new_project
   ```

## Exhibit C rules

- **Body rows**: We match the template row by keyword (e.g. "underground", "rough-in", "insulation", "final") in the Services cell and set Visits and Total from your JSON.
- **Total row**: We set Visits = sum of all row visits and Total = that sum × price_per_visit. No magic numbers.

## St. Joseph's

- Config: `st_josephs_capitol_hill_phase1.json`
- Regenerate: `python regenerate_st_josephs_proposal.py` (used by the master pipeline).
