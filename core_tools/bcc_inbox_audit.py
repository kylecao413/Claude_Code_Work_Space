"""
Read-only IMAP audit of admin@ and ycao@ buildingcodeconsulting.com.

Produces:
  Pending_Approval/_audit_report.md   — summary briefing for Kyle
  Pending_Approval/_audit_data.json   — machine-readable per-recipient record
"""

from __future__ import annotations

import email
import email.utils
import imaplib
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from email.header import decode_header, make_header
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

IMAP_HOST = "imap.privateemail.com"
IMAP_PORT = 993
SINCE = "01-Feb-2026"

ACCOUNTS = [
    {"label": "admin",
     "user": os.environ["PRIV_MAIL1_USER"],
     "pass": os.environ["PRIV_MAIL1_PASS"]},
    {"label": "ycao",
     "user": os.environ["PRIV_MAIL2_USER"],
     "pass": os.environ["PRIV_MAIL2_PASS"]},
]

BCC_ADDRS = {a["user"].lower() for a in ACCOUNTS}


def decode_str(s) -> str:
    if s is None:
        return ""
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return str(s)


def addr_only(s: str) -> str:
    m = re.search(r"<([^>]+)>", s)
    if m:
        return m.group(1).strip().lower()
    m = re.search(r"[\w\.\-+]+@[\w\.\-]+", s)
    return m.group(0).lower() if m else ""


def all_addrs(s: str) -> list[str]:
    return [a.strip().lower() for a in re.findall(r"[\w\.\-+]+@[\w\.\-]+", s or "")]


def parse_date(s: str):
    try:
        return email.utils.parsedate_to_datetime(s)
    except Exception:
        return None


def norm_subject(s: str) -> str:
    return re.sub(r"^\s*(re|fwd|fw)\s*:\s*", "", s, flags=re.I).strip()


def classify_subject(subj: str) -> str:
    s = subj.lower()
    if s.startswith("re:") or s.startswith("fwd:") or s.startswith("fw:"):
        return "reply_or_fwd"
    if "third-party code compliance inspection proposal" in s:
        return "bc_proposal"
    if s.startswith("following up"):
        return "followup"
    if "third-party inspection services for" in s or "third-party plan review" in s:
        return "cw_intro"
    return "other"


def fetch_headers(M: imaplib.IMAP4_SSL, folder: str) -> list[dict]:
    out = []
    typ, _ = M.select(folder, readonly=True)
    if typ != "OK":
        return out
    typ, data = M.search(None, f'(SINCE {SINCE})')
    if typ != "OK" or not data or not data[0]:
        return out
    uids = data[0].split()
    if not uids:
        return out
    BATCH = 200
    for i in range(0, len(uids), BATCH):
        chunk = b",".join(uids[i:i + BATCH])
        typ, msg_data = M.fetch(chunk,
            "(BODY.PEEK[HEADER.FIELDS (FROM TO CC SUBJECT DATE MESSAGE-ID IN-REPLY-TO REFERENCES)])")
        if typ != "OK":
            continue
        for item in msg_data:
            if not isinstance(item, tuple):
                continue
            raw = item[1]
            try:
                msg = email.message_from_bytes(raw)
            except Exception:
                continue
            # extract uid for this entry from the response prefix
            prefix = item[0].decode("ascii", errors="ignore") if isinstance(item[0], bytes) else str(item[0])
            mu = re.search(r"\b(\d+)\s+\(", prefix)
            uid = mu.group(1) if mu else ""
            out.append({
                "uid": uid,
                "folder": folder,
                "from": decode_str(msg.get("From", "")),
                "to": decode_str(msg.get("To", "")),
                "cc": decode_str(msg.get("Cc", "")),
                "subject": decode_str(msg.get("Subject", "")),
                "date": msg.get("Date", ""),
                "message_id": (msg.get("Message-ID") or "").strip(),
                "in_reply_to": (msg.get("In-Reply-To") or "").strip(),
                "references": (msg.get("References") or "").strip(),
            })
    return out


def fetch_snippet(M: imaplib.IMAP4_SSL, folder: str, uid: str, max_len: int = 400) -> str:
    """Fetch first ~400 chars of plaintext body for one message (for reply classification).
    Properly parses MIME — walks multipart structure, takes first text/plain payload,
    decodes Content-Transfer-Encoding."""
    if not uid:
        return ""
    M.select(folder, readonly=True)
    typ, data = M.fetch(uid.encode(), "(BODY.PEEK[])")
    if typ != "OK" or not data:
        return ""
    raw = b""
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], (bytes, bytearray)):
            raw = item[1]
            break
    if not raw:
        return ""

    try:
        msg = email.message_from_bytes(raw)
    except Exception:
        return ""

    plain_payload = None
    html_payload = None
    if msg.is_multipart():
        for part in msg.walk():
            ctype = (part.get_content_type() or "").lower()
            if part.get_content_disposition() == "attachment":
                continue
            if ctype == "text/plain" and plain_payload is None:
                try:
                    plain_payload = part.get_payload(decode=True)
                except Exception:
                    pass
            elif ctype == "text/html" and html_payload is None:
                try:
                    html_payload = part.get_payload(decode=True)
                except Exception:
                    pass
            if plain_payload:
                break
    else:
        try:
            plain_payload = msg.get_payload(decode=True)
        except Exception:
            plain_payload = None

    raw_text = plain_payload or html_payload or b""
    if not raw_text:
        return ""

    # Determine charset
    charset = msg.get_content_charset() or "utf-8"
    try:
        text = raw_text.decode(charset, errors="ignore")
    except (LookupError, Exception):
        text = raw_text.decode("utf-8", errors="ignore")

    # If HTML, strip tags
    if not plain_payload and html_payload:
        text = re.sub(r"<[^>]+>", " ", text)

    # Strip quoted/leading reply markers
    text = re.sub(r"^>.*$", "", text, flags=re.MULTILINE)
    # Strip "On <date> ... wrote:" quote-headers and everything after
    text = re.split(r"\n\s*On .{0,80}wrote:\s*\n", text, maxsplit=1)[0]
    text = re.split(r"\n\s*From:\s+.{0,200}\n\s*Sent:", text, maxsplit=1)[0]

    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def classify_reply(snippet: str) -> str:
    """Best-effort classification: declined / interested / auto / unclear."""
    s = snippet.lower()
    auto_markers = (
        "out of office", "out-of-office", "automatic reply", "auto-reply",
        "i am out", "currently away", "i'm out", "vacation", "holiday",
        "delivery has failed", "undeliverable", "could not be delivered",
        "mailer-daemon",
    )
    if any(k in s for k in auto_markers):
        return "auto"
    decline_markers = (
        "not interested", "no thank", "no thanks", "not at this time",
        "won't be needing", "won't need", "we have selected", "already selected",
        "already chosen", "pass on this", "decline", "remove me", "unsubscribe",
        "do not contact", "go with another", "going with another",
        "not pursuing", "not moving forward",
    )
    if any(k in s for k in decline_markers):
        return "declined"
    interested_markers = (
        "send the proposal", "interested", "send us the proposal", "let's set up",
        "schedule a call", "happy to chat", "let's talk", "give me a call",
        "love to learn more", "tell me more", "look forward", "schedule",
        "send pricing", "send fee", "what's your fee", "what is your fee",
        "send me a proposal", "send a proposal", "love to see", "yes please",
        "we'd like", "we would like", "please send", "would love",
    )
    if any(k in s for k in interested_markers):
        return "interested"
    return "unclear"


def main():
    all_msgs = []
    conns = {}
    for acct in ACCOUNTS:
        M = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        M.login(acct["user"], acct["pass"])
        conns[acct["label"]] = M
        for folder in ("INBOX", "Sent"):
            try:
                msgs = fetch_headers(M, folder)
            except Exception as e:
                print(f"[{acct['label']}/{folder}] ERROR: {e}")
                msgs = []
            for m in msgs:
                m["account"] = acct["label"]
            all_msgs.extend(msgs)
            print(f"[{acct['label']}/{folder}] {len(msgs)}")

    # Identify outbound set
    # Outbound = From: BCC addr AND at least one non-BCC recipient (To/Cc)
    outbound = []
    inbound = []
    for m in all_msgs:
        from_a = addr_only(m["from"])
        recipients = set(all_addrs(m["to"])) | set(all_addrs(m["cc"]))
        non_bcc_recips = recipients - BCC_ADDRS
        m["recipients_non_bcc"] = sorted(non_bcc_recips)
        if from_a in BCC_ADDRS:
            if non_bcc_recips:
                outbound.append(m)
            # else: self-traffic, drop
        else:
            inbound.append(m)

    # Dedupe outbound by Message-ID, prefer admin/Sent over inbox-CC view (more complete recipients)
    by_mid = {}
    for m in outbound:
        key = m.get("message_id") or f"{m['subject']}|{m['date']}|{','.join(m['recipients_non_bcc'])}"
        prev = by_mid.get(key)
        if prev is None:
            by_mid[key] = m
        else:
            # prefer Sent folder (originator copy) over INBOX (CC copy)
            if "sent" in m["folder"].lower() and "sent" not in prev["folder"].lower():
                by_mid[key] = m
    outbound = list(by_mid.values())

    # Also dedupe inbound by message-id
    in_by_mid = {}
    for m in inbound:
        key = m.get("message_id") or f"{m['subject']}|{m['date']}|{m['from']}"
        in_by_mid.setdefault(key, m)
    inbound = list(in_by_mid.values())

    # Group outbound: by primary recipient (first non-BCC addr) + subject category
    # Build the per-thread/per-recipient record
    sent_msgids = {m["message_id"] for m in outbound if m["message_id"]}
    sent_by_normsubj = defaultdict(list)
    for m in outbound:
        sent_by_normsubj[norm_subject(m["subject"])].append(m)

    # Detect replies: inbound where IRT/References hits a sent-msgid OR norm_subject matches
    replies = []
    for m in inbound:
        irt = m.get("in_reply_to", "")
        refs = m.get("references", "")
        ref_ids = set(re.findall(r"<[^>]+>", refs))
        if irt:
            ref_ids.add(irt)
        is_reply = bool(ref_ids & sent_msgids)
        if not is_reply:
            ns = norm_subject(m["subject"])
            if ns in sent_by_normsubj:
                is_reply = True
        if is_reply:
            replies.append(m)

    # Fetch snippets for replies (small fetch — 1 IMAP call per reply, but limited count)
    print(f"\nFetching {len(replies)} reply bodies for classification...")
    for r in replies:
        acct_lbl = r["account"]
        M = conns.get(acct_lbl)
        try:
            r["snippet"] = fetch_snippet(M, r["folder"], r["uid"]) if M else ""
        except Exception:
            r["snippet"] = ""
        r["reply_class"] = classify_reply(r["snippet"])

    # Aggregate per recipient
    # recipient_record[email] = {
    #   sends: [{date, type, subject, attachment_likely}],
    #   latest_send_date,
    #   replies: [{date, snippet, class}],
    # }
    recipient_record = defaultdict(lambda: {"sends": [], "replies": [], "company_subjects": set()})
    for m in outbound:
        for r_addr in m["recipients_non_bcc"]:
            rec = recipient_record[r_addr]
            rec["sends"].append({
                "date": m["date"],
                "subject": m["subject"],
                "type": classify_subject(m["subject"]),
                "msgid": m["message_id"],
                "account": m["account"],
                "folder": m["folder"],
            })
            rec["company_subjects"].add(norm_subject(m["subject"]))

    for r in replies:
        from_a = addr_only(r["from"])
        rec = recipient_record[from_a]
        rec["replies"].append({
            "date": r["date"],
            "subject": r["subject"],
            "snippet": r["snippet"],
            "class": r["reply_class"],
        })

    # ---- Build briefing ----
    out = []
    out.append(f"# BCC Outreach Audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    out.append(f"Source: IMAP `imap.privateemail.com` for `admin@` + `ycao@`. "
               f"`SINCE {SINCE}`. Outbound = From=BCC addr & at least 1 non-BCC recipient.\n")

    out.append("## Headline numbers\n")
    out.append(f"- Distinct outbound emails: **{len(outbound)}**")
    by_type = defaultdict(int)
    for m in outbound:
        by_type[classify_subject(m["subject"])] += 1
    for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]):
        out.append(f"  - `{k}`: {v}")
    out.append(f"- Inbound non-BCC messages since {SINCE}: **{len(inbound)}**")
    out.append(f"- Detected replies to our outbound: **{len(replies)}**")
    by_class = defaultdict(int)
    for r in replies:
        by_class[r["reply_class"]] += 1
    for k, v in sorted(by_class.items(), key=lambda kv: -kv[1]):
        out.append(f"  - reply `{k}`: {v}")

    # Bucket recipients
    bucket_interested = []
    bucket_declined = []
    bucket_auto = []
    bucket_unclear_reply = []
    bucket_no_reply = []
    for r_addr, rec in recipient_record.items():
        if not rec["sends"]:
            continue
        replies_list = rec["replies"]
        if not replies_list:
            bucket_no_reply.append((r_addr, rec))
            continue
        classes = {r["class"] for r in replies_list}
        if "interested" in classes:
            bucket_interested.append((r_addr, rec))
        elif "declined" in classes:
            bucket_declined.append((r_addr, rec))
        elif "auto" in classes and len(classes) == 1:
            bucket_auto.append((r_addr, rec))
        else:
            bucket_unclear_reply.append((r_addr, rec))

    def latest_date(rec) -> datetime:
        ds = [parse_date(s["date"]) for s in rec["sends"]]
        ds = [d for d in ds if d]
        return max(ds) if ds else datetime.min.replace(tzinfo=timezone.utc)

    def fmt_recipient(r_addr, rec):
        sends = rec["sends"]
        sends_sorted = sorted(sends, key=lambda s: parse_date(s["date"]) or datetime.min.replace(tzinfo=timezone.utc))
        last = sends_sorted[-1]
        d = parse_date(last["date"])
        ds = d.strftime("%Y-%m-%d") if d else last["date"][:10]
        types = sorted({s["type"] for s in sends})
        # extract project key from subject
        proj = re.sub(r".*?\bfor\b\s+", "", last["subject"], flags=re.I)
        proj = re.sub(r"\s*[/|]\s*BCC.*$", "", proj, flags=re.I).strip()
        proj = proj[:80]
        line = f"- **{r_addr}** — `{ds}` last send ({len(sends)} sends, types: {','.join(types)}) — {proj}"
        for r in rec["replies"]:
            rd = parse_date(r["date"])
            rds = rd.strftime("%Y-%m-%d") if rd else r["date"][:10]
            sn = (r["snippet"] or "").replace("\n", " ").strip()[:160]
            line += f"\n    - reply `{rds}` [`{r['class']}`]: {sn}"
        return line

    out.append("\n## Bucket A — REPLIED, looks INTERESTED (act now)\n")
    if not bucket_interested:
        out.append("_(none)_\n")
    for r_addr, rec in sorted(bucket_interested, key=lambda x: latest_date(x[1]), reverse=True):
        out.append(fmt_recipient(r_addr, rec))

    out.append("\n## Bucket B — REPLIED, DECLINED (skip)\n")
    if not bucket_declined:
        out.append("_(none)_\n")
    for r_addr, rec in sorted(bucket_declined, key=lambda x: latest_date(x[1]), reverse=True):
        out.append(fmt_recipient(r_addr, rec))

    out.append("\n## Bucket C — REPLIED, UNCLEAR (Kyle to read)\n")
    if not bucket_unclear_reply:
        out.append("_(none)_\n")
    for r_addr, rec in sorted(bucket_unclear_reply, key=lambda x: latest_date(x[1]), reverse=True):
        out.append(fmt_recipient(r_addr, rec))

    out.append("\n## Bucket D — REPLIED, AUTO/OOO only (treat as no reply)\n")
    out.append(f"_(count: {len(bucket_auto)})_\n")

    out.append("\n## Bucket E — SENT, NO REPLY (followup-eligible)\n")
    out.append(f"_(count: {len(bucket_no_reply)} recipients — listing top 30 by latest send)_\n")
    bucket_no_reply.sort(key=lambda x: latest_date(x[1]), reverse=True)
    for r_addr, rec in bucket_no_reply[:30]:
        out.append(fmt_recipient(r_addr, rec))

    # Cross-reference with 36 BC drafts in Pending_Approval/Outbound/
    out.append("\n## Bucket F — DRAFTS in Pending_Approval that match NO outbound (probably never sent)\n")
    pending = list((ROOT / "Pending_Approval" / "Outbound").glob("BC_Proposal_*_Draft.md"))
    sent_subj_norms = set(sent_by_normsubj.keys())
    not_matched = []
    for p in pending:
        # try to extract project name from filename
        name = p.stem.replace("BC_Proposal_", "").replace("_Draft", "").replace("_", " ")
        # search if any outbound subject contains a substring of this project
        proj_key = name.lower()
        matched = any(proj_key[:25].lower() in (s or "").lower() for s in sent_subj_norms) \
                  or any(proj_key.split(" - ")[0][:25].lower() in (s or "").lower() for s in sent_subj_norms)
        if not matched:
            not_matched.append((p.name, name))
    if not not_matched:
        out.append("_(all drafts have a matching outbound — none confirmed unsent)_\n")
    else:
        out.append(f"_(count: {len(not_matched)})_\n")
        for fname, name in sorted(not_matched):
            out.append(f"- `{fname}` — `{name}`")

    # write
    report_path = ROOT / "Pending_Approval" / "_audit_report.md"
    report_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    data = {
        "generated_at": datetime.now().isoformat(),
        "outbound_count": len(outbound),
        "inbound_count": len(inbound),
        "replies_count": len(replies),
        "buckets": {
            "interested": [r for r, _ in bucket_interested],
            "declined": [r for r, _ in bucket_declined],
            "unclear": [r for r, _ in bucket_unclear_reply],
            "auto_only": [r for r, _ in bucket_auto],
            "no_reply": [r for r, _ in bucket_no_reply],
        },
        "recipients": {
            r: {
                "sends": rec["sends"],
                "replies": rec["replies"],
            } for r, rec in recipient_record.items()
        },
    }
    json_path = ROOT / "Pending_Approval" / "_audit_data.json"
    json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # cleanup
    for M in conns.values():
        try:
            M.logout()
        except Exception:
            pass

    print(f"\nReport: {report_path}")
    print(f"Data:   {json_path}")
    print(f"  outbound={len(outbound)} inbound={len(inbound)} replies={len(replies)}")
    print(f"  Interested={len(bucket_interested)} Declined={len(bucket_declined)} "
          f"Unclear={len(bucket_unclear_reply)} Auto={len(bucket_auto)} "
          f"NoReply={len(bucket_no_reply)}")


if __name__ == "__main__":
    main()
