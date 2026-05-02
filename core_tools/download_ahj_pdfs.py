"""
Walk PE_State_Applications/{State}/AHJs/{AHJ}/ folders, parse every
manifest (`forms/_TO_DOWNLOAD.md`, `forms/URLS.txt`, `README.md`), and
download every linked PDF/document into the appropriate `forms/` or
`templates/` subfolder. Concurrent, skips existing files, tolerant of
404s and timeouts. Writes a summary report at the end.
"""

from __future__ import annotations

import concurrent.futures
import re
import sys
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent / "PE_State_Applications"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT = 60
MAX_WORKERS = 8

CURL_LINE_RE = re.compile(
    r'curl[^\n]*?-o\s+(?P<dest>[^\s"]+|"[^"]+")\s+"(?P<url>[^"]+)"'
)
SAVE_AS_RE = re.compile(r"Save as:\s*(\S+)", re.IGNORECASE)
URL_RE = re.compile(r"https?://[^\s\)\]\>\"<]+")
PDFISH_HOSTS = (
    "widen.net",
    "documentcenter/view",
    "fileuploads",
    "pdffiles",
    "/forms/",
    ".pdf",
)


def looks_like_doc(url: str) -> bool:
    low = url.lower()
    return any(tag in low for tag in PDFISH_HOSTS)


def filename_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = parsed.path.rstrip("/").rsplit("/", 1)[-1]
    name = urllib.parse.unquote(name) or "download"
    if "." not in name:
        name += ".pdf"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def collect_jobs(ahj_dir: Path) -> list[tuple[str, Path]]:
    """Return (url, dest_path) jobs for one AHJ folder."""
    jobs: dict[str, Path] = {}
    forms_dir = ahj_dir / "forms"
    templates_dir = ahj_dir / "templates"
    forms_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)

    todo = forms_dir / "_TO_DOWNLOAD.md"
    if todo.exists():
        text = todo.read_text(encoding="utf-8", errors="replace")
        for m in CURL_LINE_RE.finditer(text):
            dest = m.group("dest").strip('"')
            url = m.group("url")
            dest_path = (
                templates_dir / Path(dest).name
                if "templates" in dest
                else forms_dir / Path(dest).name
            )
            jobs.setdefault(url, dest_path)

    urls_txt = forms_dir / "URLS.txt"
    if urls_txt.exists():
        text = urls_txt.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            url_match = URL_RE.search(lines[i])
            if url_match:
                url = url_match.group(0).rstrip(".,);")
                dest_name = None
                for j in range(i + 1, min(i + 4, len(lines))):
                    sa = SAVE_AS_RE.search(lines[j])
                    if sa:
                        dest_name = sa.group(1)
                        break
                if dest_name is None:
                    dest_name = filename_from_url(url)
                low_name = dest_name.lower()
                dest_path = (
                    templates_dir / dest_name
                    if any(k in low_name for k in ("template", "report", "statement_of"))
                    else forms_dir / dest_name
                )
                jobs.setdefault(url, dest_path)
            i += 1

    readme = ahj_dir / "README.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8", errors="replace")
        for m in URL_RE.finditer(text):
            url = m.group(0).rstrip(".,);]")
            if not looks_like_doc(url):
                continue
            if url in jobs:
                continue
            dest_name = filename_from_url(url)
            low = (url + dest_name).lower()
            target_dir = (
                templates_dir
                if any(k in low for k in ("report", "statement", "letter", "template"))
                else forms_dir
            )
            jobs.setdefault(url, target_dir / dest_name)

    return list(jobs.items())


def download(url: str, dest: Path) -> tuple[str, Path, str]:
    if dest.exists() and dest.stat().st_size > 256:
        return ("skip", dest, "exists")
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException as exc:
        return ("err", dest, f"req:{exc.__class__.__name__}")
    if r.status_code != 200:
        return ("err", dest, f"http:{r.status_code}")
    content = r.content
    if len(content) < 256:
        return ("err", dest, f"tiny:{len(content)}")
    ctype = r.headers.get("Content-Type", "").lower()
    if "html" in ctype and not content.lstrip().startswith(b"%PDF"):
        return ("err", dest, f"html:{ctype}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return ("ok", dest, f"{len(content)//1024}KB")


def main() -> int:
    if not ROOT.exists():
        print(f"ROOT not found: {ROOT}", file=sys.stderr)
        return 2

    all_jobs: list[tuple[str, Path]] = []
    for state_dir in sorted(ROOT.iterdir()):
        if not state_dir.is_dir() or state_dir.name not in {"FL", "TX", "NC", "SC"}:
            continue
        ahj_root = state_dir / "AHJs"
        if not ahj_root.exists():
            continue
        for ahj in sorted(ahj_root.iterdir()):
            if not ahj.is_dir():
                continue
            jobs = collect_jobs(ahj)
            for url, dest in jobs:
                all_jobs.append((url, dest))

    print(f"Total jobs: {len(all_jobs)}")
    results: dict[str, list[tuple[str, Path, str]]] = {"ok": [], "skip": [], "err": []}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(download, u, d): (u, d) for u, d in all_jobs}
        for fut in concurrent.futures.as_completed(futs):
            status, dest, info = fut.result()
            results[status].append((status, dest, info))
            tag = {"ok": "OK ", "skip": "SKP", "err": "ERR"}[status]
            print(f"{tag} {dest.relative_to(ROOT)}  [{info}]")

    print("\n=== SUMMARY ===")
    for k in ("ok", "skip", "err"):
        print(f"{k}: {len(results[k])}")
    if results["err"]:
        print("\n--- failures ---")
        for _, dest, info in sorted(results["err"], key=lambda r: str(r[1])):
            print(f"  {dest.relative_to(ROOT)}  [{info}]")
    return 0 if not results["err"] else 1


if __name__ == "__main__":
    sys.exit(main())
