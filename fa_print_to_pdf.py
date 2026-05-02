"""Download FA deficiency Google Sheet (already fetched via Drive MCP, JSON
wrapper saved by the harness), unwrap base64 → save as xlsx, then drive Excel
to print just the filled rows to PDF using Kyle's canonical recipe:
  Print Selection + Narrow Margins + Fit All Columns on One Page +
  Microsoft Print to PDF, landscape, into the project's Wrap up folder.
"""
from __future__ import annotations
import base64, json, os, sys
from pathlib import Path

WRAP_DIR = Path(r"C:\Users\Kyle Cao\DC Business\Building Code Consulting\Projects\Nery Soto Fire Protection\1522 Rhode Island Ave NE - PR\Wrap up")
PDF_OUT = WRAP_DIR / "1522 Rhode Island Ave NE FA Plan Review Deficiency Report.pdf"
XLSX_OUT = WRAP_DIR / "_fa_temp.xlsx"
SRC_JSON = Path(r"C:\Users\Kyle Cao\.claude\projects\C--Users-Kyle-Cao-DC-Business-Building-Code-Consulting-Business-Automation\3f19467d-a245-4a99-89c8-811e6094cc7e\tool-results\mcp-claude_ai_Google_Drive-download_file_content-1777418155546.txt")


def unwrap_to_xlsx() -> Path:
    with open(SRC_JSON, "r", encoding="utf-8") as f:
        payload = json.load(f)
    blob_b64 = payload["content"][0]["embeddedResource"]["contents"]["blob"]
    data = base64.b64decode(blob_b64)
    XLSX_OUT.write_bytes(data)
    return XLSX_OUT


def find_filled_range(ws, header_rows: int = 4) -> tuple[int, int, int, int]:
    """Return (first_row, last_row, first_col, last_col).

    Last-row detection: a data row counts as 'filled' only if cells OUTSIDE
    column A have non-empty text. Column A is the # / row-number column on
    the deficiency template — its presence alone (just a number) is a
    formatted-but-empty row Kyle excludes from print. Header rows above
    `header_rows` are kept regardless.
    """
    used = ws.UsedRange
    first_row = used.Row
    first_col = used.Column
    last_row = used.Row + used.Rows.Count - 1
    last_col = used.Column + used.Columns.Count - 1
    real_last = first_row + header_rows - 1  # at minimum keep header band
    # Skip the leftmost padding column and the # column (cols 1 and 2 in the
    # BCC deficiency template). Real content lives in col 3+ (Initial Comment,
    # Client Response, Page #, 2nd Review, Client Response, 3rd Review).
    content_start_col = max(first_col + 2, 3)
    for r in range(last_row, first_row + header_rows - 1, -1):
        row_has_real_content = False
        for c in range(content_start_col, last_col + 1):
            v = ws.Cells(r, c).Value
            if v is None:
                continue
            if isinstance(v, str) and not v.strip():
                continue
            row_has_real_content = True
            break
        if row_has_real_content:
            real_last = r
            break
    return first_row, real_last, first_col, last_col


def print_to_pdf(xlsx_path: Path) -> Path:
    import win32com.client as win32
    excel = win32.gencache.EnsureDispatch("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        wb = excel.Workbooks.Open(str(xlsx_path), ReadOnly=True)
        try:
            # Use the active/first sheet; deficiency reports are single-sheet.
            ws = wb.Worksheets(1)
            r0, r1, c0, c1 = find_filled_range(ws)
            print(f"Filled range: rows {r0}-{r1}, cols {c0}-{c1}")
            rng = ws.Range(ws.Cells(r0, c0), ws.Cells(r1, c1))
            ws.PageSetup.PrintArea = rng.Address
            # Kyle's recipe
            ws.PageSetup.Orientation = 2  # xlLandscape
            ws.PageSetup.Zoom = False
            ws.PageSetup.FitToPagesWide = 1
            ws.PageSetup.FitToPagesTall = False  # let it span as many vertical pages as needed
            # Narrow margins (Excel's "Narrow" preset = 0.25" left/right, 0.75" top/bottom)
            ws.PageSetup.LeftMargin = excel.InchesToPoints(0.25)
            ws.PageSetup.RightMargin = excel.InchesToPoints(0.25)
            ws.PageSetup.TopMargin = excel.InchesToPoints(0.75)
            ws.PageSetup.BottomMargin = excel.InchesToPoints(0.75)
            ws.PageSetup.HeaderMargin = excel.InchesToPoints(0.3)
            ws.PageSetup.FooterMargin = excel.InchesToPoints(0.3)
            # Export PDF (xlTypePDF = 0)
            wb.ExportAsFixedFormat(0, str(PDF_OUT))
        finally:
            wb.Close(SaveChanges=False)
    finally:
        excel.Quit()
    return PDF_OUT


def main():
    xlsx = unwrap_to_xlsx()
    print(f"xlsx → {xlsx}  ({xlsx.stat().st_size} bytes)")
    pdf = print_to_pdf(xlsx)
    print(f"pdf  → {pdf}  ({pdf.stat().st_size} bytes)")
    # Cleanup temp xlsx
    try:
        xlsx.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    main()
