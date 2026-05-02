"""Fill FL / SC / TX PE application PDFs from Master_Info.yaml.

DC and MD are already licensed — they receive NCEES Record transmittal only
(add Fire Protection discipline to existing PE license) and need no PDF here.

Run: python fill_pdfs.py → writes {State}_PREFILLED.pdf in each state folder.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject, TextStringObject

HERE = Path(__file__).resolve().parent


def _load() -> dict:
    with open(HERE / "Master_Info.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fill(src: Path, dst: Path, text_map: dict[str, str], check_map: dict[str, bool | str] | None = None) -> None:
    """Fill a PDF's text fields (text_map) and checkbox/radio fields (check_map).

    check_map values:
      - True            → set to /Yes
      - False / absent  → leave unchecked
      - str (e.g. /Male, /Home, /Choice4) → set to that exact export name
        (use when the form's button group has named options beyond Yes/Off)
    """
    reader = PdfReader(str(src))
    writer = PdfWriter(clone_from=reader)
    if "/AcroForm" in writer._root_object:
        writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)

    str_map = {k: ("" if v is None else str(v)) for k, v in text_map.items()}

    for page in writer.pages:
        try:
            writer.update_page_form_field_values(page, str_map)
        except Exception as e:  # noqa: BLE001
            print(f"  warn (text): {e}")

    if check_map:
        checked: dict[str, NameObject] = {}
        for k, v in check_map.items():
            if v is True:
                checked[k] = NameObject("/Yes")
            elif isinstance(v, str) and v:
                # explicit export name like "/Male", "/Home", "/Choice4"
                checked[k] = NameObject(v if v.startswith("/") else f"/{v}")
        if checked:
            for page in writer.pages:
                try:
                    writer.update_page_form_field_values(page, checked)
                except Exception as e:  # noqa: BLE001
                    print(f"  warn (checkbox): {e}")

    with open(dst, "wb") as f:
        writer.write(f)
    print(f"  wrote {dst.name}")


def fill_fl(info: dict) -> None:
    p = info["personal"]
    b = info["business"]
    edu = info["education"]
    ex = info["exams"]
    lic = info["licenses"]
    emp = info["employment"]
    ref = info["references"]

    # Education rows (4 available on form)
    def edu_field(i: int, key: str) -> str:
        if i >= len(edu):
            return ""
        e = edu[i]
        return {
            "school": e.get("school", ""),
            "degree": e.get("degree", ""),
            "major": e.get("major", ""),
            "grad": e.get("grad_date", ""),
        }.get(key, "")

    # Exam rows — chronological: FE, PE Civil, PE Electrical, PE FP
    # (reordered so date order is ascending on the form)
    exam_rows = [
        ("FE", ex["fe"]["location"], ex["fe"]["date"], ex["fe"]["discipline"]),
        ("PE", ex["pe_civil"]["location"], ex["pe_civil"]["date"], ex["pe_civil"]["discipline"]),
        ("PE", ex["pe_electrical"]["location"], ex["pe_electrical"]["date"], ex["pe_electrical"]["discipline"]),
        ("PE", ex["pe_fire"]["location"], ex["pe_fire"]["date"], ex["pe_fire"]["discipline"]),
    ]

    # Employment (up to 8 rows on FL form)
    def emp_field(i: int, key: str) -> str:
        if i >= len(emp):
            return ""
        E = emp[i]
        return {
            "from": E.get("from_date", ""),
            "to": E.get("to_date", ""),
            "months": str(E.get("months_full_time", "")),
            "employer": E.get("employer", ""),
            "verifier": E.get("verifying_engineer", ""),
            "ver_lic": E.get("verifier_license", ""),
        }.get(key, "")

    text_map: dict[str, str] = {
        # Name block
        "First": p["first"],
        "Middle": p["middle"],
        "Last": p["last"],
        "Other Full Names I amhave been known as": p["other_names"],
        # Home address
        "Number and Street": p["home_street"],
        "AptLot No": "",
        "City": p["home_city"],
        "State": p["home_state"],
        "Zip Code": p["home_zip"],
        "HOME TELEPHONE NUMBER": p["home_phone"],
        "BUSINESS TELEPHONE NUMBER": b["phone"],
        "DATE OF BIRTH MMDDYYYY": p["dob_nohyp"],
        # Email (personal) + SSN
        "email address": p["personal_email"],
        "Text2": p["ssn"],
        # NCEES ID
        "NO If so please list NCEES ID Number": info["ncees"]["id"],
        # Native language
        "native languate": p["native_language"],
        # Education rows 1-4
        "Names of Colleges  Universities Attended and CityStateCountryRow1": edu_field(0, "school"),
        "Degree Received eg BS MS PhDRow1": edu_field(0, "degree"),
        "Engineering discipline degree major": edu_field(0, "major"),
        "Graduation Date MMYYYY": edu_field(0, "grad"),
        "Names of Colleges  Universities Attended and CityStateCountryRow2": edu_field(1, "school"),
        "Degree Received eg BS MS PhDRow2": edu_field(1, "degree"),
        "Engineering discipline degree major_2": edu_field(1, "major"),
        "Graduation Date MMYYYY_2": edu_field(1, "grad"),
        "Names of Colleges  Universities Attended and CityStateCountryRow3": edu_field(2, "school"),
        "Degree Received eg BS MS PhDRow3": edu_field(2, "degree"),
        "Engineering discipline degree major_3": edu_field(2, "major"),
        "Graduation Date MMYYYY_3": edu_field(2, "grad"),
        "Names of Colleges  Universities Attended and CityStateCountryRow4": edu_field(3, "school"),
        "Degree Received eg BS MS PhDRow4": edu_field(3, "degree"),
        "Engineering discipline degree major_4": edu_field(3, "major"),
        "Graduation Date MMYYYY_4": edu_field(3, "grad"),
        # Exam rows 1-4
        "Examination eg FE PE SERow1": exam_rows[0][0],
        "Exam Location City StateRow1": exam_rows[0][1],
        "Date Taken MMYYYYRow1": exam_rows[0][2],
        "Exam Discipline": exam_rows[0][3],
        "Examination eg FE PE SERow2": exam_rows[1][0],
        "Exam Location City StateRow2": exam_rows[1][1],
        "Date Taken MMYYYYRow2": exam_rows[1][2],
        "Exam Discipline_2": exam_rows[1][3],
        "Examination eg FE PE SERow3": exam_rows[2][0],
        "Exam Location City StateRow3": exam_rows[2][1],
        "Date Taken MMYYYYRow3": exam_rows[2][2],
        "Exam Discipline_3": exam_rows[2][3],
        "Examination eg FE PE SERow4": exam_rows[3][0],
        "Exam Location City StateRow4": exam_rows[3][1],
        "Date Taken MMYYYYRow4": exam_rows[3][2],
        "Exam Discipline_4": exam_rows[3][3],
        # Licenses currently held (disclosure, required by FL): VA / DC / MD.
        # One license # per state, regardless of how many disciplines.
        "StateRow1": lic[0].get("state", ""),
        "License NoRow1": lic[0].get("number", ""),
        "Year Issued YYYYRow1": lic[0].get("year_issued", ""),
        "Type of LicenseRow1": lic[0].get("type", ""),
        "License Status eg active inactive retired revoked suspendedRow1": lic[0].get("status", ""),
        "StateRow2": lic[1].get("state", ""),       # DC
        "License NoRow2": lic[1].get("number", ""),
        "Year Issued YYYYRow2": lic[1].get("year_issued", ""),
        "Type of LicenseRow2": lic[1].get("type", ""),
        "License Status eg active inactive retired revoked suspendedRow2": lic[1].get("status", ""),
        "StateRow3": lic[2].get("state", ""),       # MD
        "License NoRow3": lic[2].get("number", ""),
        "Year Issued YYYYRow3": lic[2].get("year_issued", ""),
        "Type of LicenseRow3": lic[2].get("type", ""),
        "License Status eg active inactive retired revoked suspendedRow3": lic[2].get("status", ""),
        # Employment rows 1-4
        "From MMDDYY": emp_field(0, "from"),
        "To MMDDYY": emp_field(0, "to"),
        "Months of Full time Experience Being Claimed": emp_field(0, "months"),
        "Employer": emp_field(0, "employer"),
        "Name of Verifying Engineer": emp_field(0, "verifier"),
        "Verifying Engineers License No  State": emp_field(0, "ver_lic"),
        "From MMDDYY_2": emp_field(1, "from"),
        "To MMDDYY_2": emp_field(1, "to"),
        "Months of Full time Experience Being Claimed_2": emp_field(1, "months"),
        "Employer_2": emp_field(1, "employer"),
        "Name of Verifying Engineer_2": emp_field(1, "verifier"),
        "Verifying Engineers License No  State_2": emp_field(1, "ver_lic"),
        "From MMDDYY_3": emp_field(2, "from"),
        "To MMDDYY_3": emp_field(2, "to"),
        "Months of Full time Experience Being Claimed_3": emp_field(2, "months"),
        "Employer_3": emp_field(2, "employer"),
        "Name of Verifying Engineer_3": emp_field(2, "verifier"),
        "Verifying Engineers License No  State_3": emp_field(2, "ver_lic"),
        "From MMDDYY_4": emp_field(3, "from"),
        "To MMDDYY_4": emp_field(3, "to"),
        "Months of Full time Experience Being Claimed_4": emp_field(3, "months"),
        "Employer_4": emp_field(3, "employer"),
        "Name of Verifying Engineer_4": emp_field(3, "verifier"),
        "Verifying Engineers License No  State_4": emp_field(3, "ver_lic"),
        # References: 3 PE slots. Use only entries with is_pe: true.
        # (Non-PE character refs stay in yaml as backups but aren't used here
        # since FL requires licensed PE references.)
    }
    pe_refs = [r for r in ref if r.get("is_pe")]
    for idx, suffix in enumerate(["", "_2", "_3"]):
        r = pe_refs[idx] if idx < len(pe_refs) else {"name": "", "license": "", "address": ""}
        text_map[f"Name of Reference Engineer{suffix}"] = r.get("name", "")
        text_map[f"Reference Engineers License No  State{suffix}"] = r.get("license", "")
        text_map[f"Reference Engineers Address{suffix}"] = r.get("address", "")

    # Checkboxes
    check_map: dict[str, bool] = {
        "Are You a NCEES Record Holder?": True,
        # Graduate Yes for each row where graduated == True
        "Graduate": edu[0].get("graduated", False) if len(edu) > 0 else False,
        "Graduate 2": edu[1].get("graduated", False) if len(edu) > 1 else False,
        "Graduate 3": edu[2].get("graduated", False) if len(edu) > 2 else False,
        "Graduate 4": edu[3].get("graduated", False) if len(edu) > 3 else False,
        # Pass exams 1-4 (all 4 passed)
        "Pass 1": True,
        "Pass 2": True,
        "Pass 3": True,
        "Pass 4": True,
    }

    _fill(HERE / "FL" / "FL_PE_Application.pdf", HERE / "FL" / "FL_PE_Application_PREFILLED.pdf", text_map, check_map)


def fill_sc(info: dict) -> None:
    p = info["personal"]
    b = info["business"]
    edu = info["education"]
    emp = info["employment"]
    ex = info["exams"]
    lic = info["licenses"]
    ref = info["references"]

    def edu_field(i: int, key: str) -> str:
        if i >= len(edu):
            return ""
        e = edu[i]
        return {
            "school": e.get("school", ""),
            "years": e.get("years_from_to", ""),
            "grad": e.get("grad_date", ""),
            "degree": f'{e.get("degree", "")} / {e.get("major", "")}',
        }.get(key, "")

    def emp_block(i: int, key: str) -> str:
        if i >= len(emp):
            return ""
        E = emp[i]
        # SubProWork = subordinate/junior engineering work; for senior roles set to "N/A".
        # ProWork = professional/responsible-charge work — uses position + project summary.
        return {
            "dates": f'{E.get("from_date", "")} - {E.get("to_date", "")}',
            "name": E.get("employer", ""),
            "sub": "N/A",
            "pro": f'{E.get("position", "")} - {E.get("projects", "")}',
            "total": str(E.get("months_full_time", "")),
        }.get(key, "")

    full_home_addr = f'{p["home_street"]}, {p["home_city"]}, {p["home_state"]} {p["home_zip"]}'
    full_biz_addr = f'{b["street"]}, {b["city"]}, {b["state"]} {b["zip"]}'

    # 5 SC reference slots — fill with the 4 PE refs + Jeff Tan as the 5th
    # (SC commonly accepts 1 character ref alongside PE refs; Kyle to verify
    # SC instructions before notarizing if all 5 must be PE).
    ref_slots: list[dict] = []
    pe_only = [r for r in ref if r.get("is_pe")]
    non_pe = [r for r in ref if not r.get("is_pe")]
    ref_slots.extend(pe_only[:4])
    if non_pe:
        ref_slots.append(non_pe[0])  # Jeff Tan
    while len(ref_slots) < 5:
        ref_slots.append({"name": "", "address": ""})

    # Engineering exam history summary (FE + 4 PE incl. one Fail)
    exam_summary = (
        f'FE Civil {ex["fe"]["date"]} {ex["fe"]["location"]} - Pass; '
        f'PE Civil-Geotech {ex["pe_civil"]["date"]} {ex["pe_civil"]["location"]} - Pass; '
        f'PE Control Systems {ex["pe_control_systems"]["date"]} {ex["pe_control_systems"]["location"]} - Fail; '
        f'PE Electrical/Computer-ECC {ex["pe_electrical"]["date"]} {ex["pe_electrical"]["location"]} - Pass; '
        f'PE Fire Protection {ex["pe_fire"]["date"]} {ex["pe_fire"]["location"]} - Pass.'
    )

    # Other-jurisdiction license summary (3 slots → VA / DC / MD)
    pe_lics = [L for L in lic if L.get("type", "").startswith("Professional Engineer")]
    def lic_summary(i: int) -> str:
        if i >= len(pe_lics):
            return ""
        L = pe_lics[i]
        return f'{L["state"]} PE {L["number"]} / {L.get("initial_issue_date", L.get("year_issued", ""))} - {L.get("status", "Active")}'

    text_map: dict[str, str] = {
        "Applicant Name": p["full_legal"],
        "Home Address": full_home_addr,
        "Home Telephone": p["home_phone"],
        "Email": p["personal_email"],
        "Business Name": b["company"],
        "Business Address": full_biz_addr,
        "Business Telephone": b["phone"],
        "Business Email": b["email"],
        "SSN": p["ssn"],
        "DOB": p["dob_slash"],
        # 5 reference rows
        "NameRow1": ref_slots[0].get("name", ""),
        "Mailing AddressRow1": ref_slots[0].get("address", ""),
        "NameRow2": ref_slots[1].get("name", ""),
        "Mailing AddressRow2": ref_slots[1].get("address", ""),
        "NameRow3": ref_slots[2].get("name", ""),
        "Mailing AddressRow3": ref_slots[2].get("address", ""),
        "NameRow4": ref_slots[3].get("name", ""),
        "Mailing AddressRow4": ref_slots[3].get("address", ""),
        "NameRow5": ref_slots[4].get("name", ""),
        "Mailing AddressRow5": ref_slots[4].get("address", ""),
        # Education rows
        "Name and Location of InstitutionRow1": edu_field(0, "school"),
        "Years Attended From  ToRow1": edu_field(0, "years"),
        "Date Graduated MonthDayYearRow1": edu_field(0, "grad"),
        "Degree ReceivedMajorRow1": edu_field(0, "degree"),
        "Name and Location of InstitutionRow2": edu_field(1, "school"),
        "Years Attended From  ToRow2": edu_field(1, "years"),
        "Date Graduated MonthDayYearRow2": edu_field(1, "grad"),
        "Degree ReceivedMajorRow2": edu_field(1, "degree"),
        "Name and Location of InstitutionRow3": edu_field(2, "school"),
        "Years Attended From  ToRow3": edu_field(2, "years"),
        "Date Graduated MonthDayYearRow3": edu_field(2, "grad"),
        "Degree ReceivedMajorRow3": edu_field(2, "degree"),
        # Disclosure detail text fields (Yes/No checkboxes left blank — Kyle ticks by hand;
        # field-name pairings are inferred and could be reversed, so polarity stays manual)
        "If so date of examination": exam_summary,
        "If so date of examination_2": f'PE Control Systems {ex["pe_control_systems"]["date"]} {ex["pe_control_systems"]["location"]} - Fail (only failed attempt; passed PE Electrical/Computer-ECC the following year).',
        "If so jurisdictiondatecert no": lic_summary(0),
        "If so jurisdictiondatecert no_2": lic_summary(1),
        "If so jurisdictiondatecert no_3": lic_summary(2),
        "If so list numberdate1": "N/A",
        "If so list numberdate": "N/A",
        "If so List COA": (
            "N/A - Building Code Consulting LLC (Virginia) is not currently registered "
            "in South Carolina. Upon issuance of the individual SC PE license, the firm "
            "will file for a SC Certificate of Authorization prior to offering or "
            "performing any engineering services within South Carolina."
        ),
        # Employment rows 0-3 (4 slots filled)
        "2DatesEmployment.0": emp_block(0, "dates"),
        "2EmpName.0": emp_block(0, "name"),
        "2SubProWork.0": emp_block(0, "sub"),
        "2ProWork.0": emp_block(0, "pro"),
        "2TotalTime.0": emp_block(0, "total"),
        "2DatesEmployment.1": emp_block(1, "dates"),
        "2EmpName.1": emp_block(1, "name"),
        "2SubProWork.1": emp_block(1, "sub"),
        "2ProWork.1": emp_block(1, "pro"),
        "2TotalTime.1": emp_block(1, "total"),
        "2DatesEmployment.2": emp_block(2, "dates"),
        "2EmpName.2": emp_block(2, "name"),
        "2SubProWork.2": emp_block(2, "sub"),
        "2ProWork.2": emp_block(2, "pro"),
        "2TotalTime.2": emp_block(2, "total"),
        "2DatesEmployment.3": emp_block(3, "dates"),
        "2EmpName.3": emp_block(3, "name"),
        "2SubProWork.3": emp_block(3, "sub"),
        "2ProWork.3": emp_block(3, "pro"),
        "2TotalTime.3": emp_block(3, "total"),
        # Engineering experience totals — 32 (BCC) + 96 (UES-CTI) + 50 (DMY) + 24 (YIDA) = 202;
        # but UES-CTI (96 mo) overlaps with BCC (32 mo) since both are concurrent self-employed
        # PIC roles. Net non-overlapping full-time: 96 + 50 + 24 = 170 months ~= 14.2 years.
        "2SubProTotal": "0",                          # no subordinate-only periods claimed
        "2ProTotal": "170",                           # responsible-charge total months
        "2Total": "170",
        "2WhatBranch": "Electrical and Computer (primary NCEES discipline); also Civil-Geotechnical and Fire Protection",
        # VLC block (legal presence)
        "NameVLC": p["full_legal"],
        "Home Address City State and Zip Code": full_home_addr,
        "OtherVLC": p["citizenship"],
        "DOB-VLC": p["dob_slash"],
        "Alien Number": p["alien_number"],
        "I94 Number": p["i94_number"],
    }

    # Unambiguous radio-style buttons (export-name values, not just /Yes)
    check_map: dict[str, bool | str] = {
        "cbSex": "/Male",
        "cbAddress": "/Home",     # personal email + home phone are primary contact per yaml
        # Yes/No disclosure checkboxes deliberately NOT auto-checked — see comment above.
        # Group1 (4 choices) also left for Kyle to pick manually before notarizing.
    }

    _fill(HERE / "SC" / "SC_PE_Comity.pdf", HERE / "SC" / "SC_PE_Comity_PREFILLED.pdf", text_map, check_map)


def fill_tx(info: dict) -> None:
    p = info["personal"]
    b = info["business"]
    edu = info["education"]
    ex = info["exams"]
    emp = info["employment"]

    full_home_citystatezip = f'{p["home_city"]}, {p["home_state"]} {p["home_zip"]}'
    full_biz_citystatezip = f'{b["city"]}, {b["state"]} {b["zip"]}'

    def edu_field(i: int, key: str) -> str:
        if i >= len(edu):
            return ""
        e = edu[i]
        return {
            "program": e.get("major", ""),
            "type": e.get("degree", ""),
            "date": e.get("grad_date", ""),
            "location": e.get("school", ""),
            "attendance": e.get("years_from_to", ""),
        }.get(key, "")

    def emp_row(i: int, key: str) -> str:
        if i >= len(emp):
            return ""
        E = emp[i]
        return {
            "dates": f'{E.get("from_date", "")} - {E.get("to_date", "")}',
            "emp": f'{E.get("employer", "")} - {E.get("position", "")}',
            "noneng": "",
            "eng": str(E.get("months_full_time", "")),
            "verifier": f'{E.get("verifying_engineer", "")}, {E.get("verifier_license", "")}',
        }.get(key, "")

    text_map = {
        "Name": p["full_legal"],
        "Email Address": p["personal_email"],
        "INS Status": p["citizenship"],
        "Card No": f'{p["alien_number"]}',
        "Full Legal Name": p["full_legal"],
        "Maiden Name": "",
        "Date of Birth": p["dob_slash"],
        "Social Security Number": p["ssn"],
        "E-mail Address": p["personal_email"],
        "Street": p["home_street"],
        "City, State, Zip": full_home_citystatezip,
        "Telephone Number": p["home_phone"],
        "Fax Number": "",
        "Employer Name": b["company"],
        "Employer Street": b["street"],
        "Employer City, State, Zip": full_biz_citystatezip,
        "Employer Telephone Number": b["phone"],
        "Employer Fax Number": "",
        "Primary Branch": "Electrical and Computer",
        "FE Where?": ex["fe"]["location"],
        "FE When?": ex["fe"]["date"],
        "PE Where?": ex["pe_electrical"]["location"],
        "PE When?": ex["pe_electrical"]["date"],
        "States With Other Current Licenses": "VA, DC, MD",
        "States With Other Expired Licenses": "None",
        "States Where Licenses Were Denied": "None",
        "States Where Disciplined": "None",
        "Primary Jurisdiction": "VA",
        "Date Transmitted": "",   # leave blank — fill by hand when you order NCEES → TX transmittal
        # Education rows
        "education degree program 1": edu_field(0, "program"),
        "education degree type 1": edu_field(0, "type"),
        "education date 1": edu_field(0, "date"),
        "education location 1": edu_field(0, "location"),
        "education attendance 1": edu_field(0, "attendance"),
        "education degree program 2": edu_field(1, "program"),
        "education degree type 2": edu_field(1, "type"),
        "education date 2": edu_field(1, "date"),
        "education location 2": edu_field(1, "location"),
        "education attendance 2": edu_field(1, "attendance"),
        "education degree program 3": edu_field(2, "program"),
        "education degree type 3": edu_field(2, "type"),
        "education date 3": edu_field(2, "date"),
        "education location 3": edu_field(2, "location"),
        "education attendance 3": edu_field(2, "attendance"),
        "education degree program 4": edu_field(3, "program"),
        "education degree type 4": edu_field(3, "type"),
        "education date 4": edu_field(3, "date"),
        "education location 4": edu_field(3, "location"),
        "education attendance 4": edu_field(3, "attendance"),
        # Employment rows 1-2
        "Reference Dates": emp_row(0, "dates"),
        "EMPLOYMENT Name Address and Position Held1": emp_row(0, "emp"),
        "NONENGINEERING TIME List Years and Months1": emp_row(0, "noneng"),
        "ENGINEERING TIME List Years and Months1": emp_row(0, "eng"),
        "NAME TELEPHONE NUMBER AND PRESENT ADDRESS OF PERSON WHO CAN VERIFY EMPLOYMENT OR UNEMPLOYMENT1": emp_row(0, "verifier"),
        "Reference Dates 2": emp_row(1, "dates"),
        "EMPLOYMENT Name Address and Position Held2": emp_row(1, "emp"),
        "NONENGINEERING TIME List Years and Months2": emp_row(1, "noneng"),
        "ENGINEERING TIME List Years and Months2": emp_row(1, "eng"),
        "NAME TELEPHONE NUMBER AND PRESENT ADDRESS OF PERSON WHO CAN VERIFY EMPLOYMENT OR UNEMPLOYMENT2": emp_row(1, "verifier"),
        "comments": (
            "Active VA PE (0402056707, disciplines: Electrical/Computer - Electronics Controls & Communications; "
            "Civil - Geotechnical; Fire Protection newly added 04/2026). NCEES Record 14-528-37 transmitted. "
            "Also holds DC and MD PE (NCEES transmittals in progress to add FP discipline there)."
        ),
    }

    check_map = {
        "currently licensed in another jurisdiction": True,
        "ncees yes": True,
        "fe yes": True,
        "pe taken": True,
        "denied no": True,
        "previous no": True,
        "Yes": False,
        "No": True,
        "mr": True,
        "military no": True,
    }

    _fill(HERE / "TX" / "TX_PE_Application.pdf", HERE / "TX" / "TX_PE_Application_PREFILLED.pdf", text_map, check_map)


def main() -> None:
    info = _load()
    print("Filling FL...")
    fill_fl(info)
    print("Filling SC...")
    fill_sc(info)
    print("Filling TX...")
    fill_tx(info)
    print("\nAll 3 PDFs regenerated. Open each and review before printing/notarizing/mailing.")


if __name__ == "__main__":
    main()
