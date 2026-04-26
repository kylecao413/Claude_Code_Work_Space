"""
kcy_outreach.py — Cold-outreach + follow-up email generators for KCY Engineer PLLC.

Parallel to BCC generators (in run_cw_leads_pipeline.py and send_cw_followups.py)
but scoped to KCY's distinct brand, service matrix, and territory.

KCY brand spec (confirmed by Kyle 2026-04-23):
  - Company: KCY Engineer PLLC
  - Sender: ycao@kcyengineer.com
  - Signature: Kyle Cao, Professional In Charge
  - Services:
      * Expedited Peer Review (renamed from "Plan Review") — nationwide
      * Third-Party Inspection — Virginia residential (Fairfax confirmed;
        other NoVA counties pending Kyle's AHJ applications); PG County MD
        residential + commercial
      * Code Consulting — up to Baltimore (north), Norfolk (south)
  - NO "BCC" references anywhere — KCY is an entirely separate brand.
  - NO mention of DC inspection (DC = BCC territory; keep the brands
    non-overlapping to avoid channel conflict).

Conventions intentionally match BCC generators so the same Telegram-review,
pending-approval, and work_log workflows apply:
  - No signature in body (email_sender.py injects brand-specific sig).
  - No ellipses; complete sentences only.
  - Always include flat-rate / per-visit billing disclaimer (for inspection).
  - Role-aware branching: GC/CM vs Developer/Owner vs Architect.
"""
from __future__ import annotations

import re

# ── Role classifier (mirrors run_cw_leads_pipeline._role_is_*) ─────────────────
def _role_is_gc_or_cm(role: str) -> bool:
    role = role or ""
    return any(r in role for r in (
        "General Contractor", "GC", "Construction Manager", "CM",
        "Construction Management", "Contractor",
    ))


def _role_is_developer_or_owner(role: str) -> bool:
    role = role or ""
    return any(r in role for r in ("Developer", "Owner"))


def _role_is_architect(role: str) -> bool:
    role = role or ""
    return "Architect" in role


def _first_name(full_name: str) -> str:
    parts = (full_name or "").strip().split()
    return parts[0] if parts else ""


# ── Shared pitch bullets ──────────────────────────────────────────────────────
BULLET_EXPERTISE = (
    "Multi-Discipline Engineering Expertise: KCY's team is led by a licensed "
    "Professional Engineer (PE) and ICC Master Code Professional (MCP) with "
    "collaborating licensed PEs across Building, Mechanical, Electrical, "
    "Plumbing, and Fire Protection disciplines. We serve as a hands-on "
    "technical resource for code compliance questions — providing professional "
    "guidance when issues arise."
)

BULLET_SCHEDULING = (
    "Responsive Scheduling: We offer same-day or next-business-day inspection "
    "availability to keep your project milestones on track."
)

BULLET_BILLING_INSPECTION = (
    "Fair, Visit-Based Billing: Inspection billing is based on actual visits "
    "completed — our fee is a flat rate per inspection visit actually performed. "
    "You will never be billed based on an upfront estimate. If your project "
    "wraps up in fewer inspections than projected, you pay only for what was done."
)

BULLET_PEER_REVIEW = (
    "Expedited Peer Review: KCY provides expedited third-party peer review for "
    "jurisdictions nationwide. Our reviews identify code deficiencies before "
    "submission — reducing agency review cycles, avoiding costly revision loops, "
    "and protecting your project schedule."
)


# ── Territory phrase helpers ──────────────────────────────────────────────────
def _inspection_territory_phrase() -> str:
    """Human-readable territory line for the inspection service.

    Kept in one place so future expansion (Arlington, Loudoun, PW, etc.)
    can be updated in a single spot.
    """
    return (
        "residential third-party inspections in Northern Virginia (Fairfax "
        "County) and full commercial + residential third-party inspections in "
        "Prince George's County, MD"
    )


def _peer_review_territory_phrase() -> str:
    return "expedited peer review for jurisdictions nationwide"


# ── Subject line generators ───────────────────────────────────────────────────
def cold_subject(project: str, service_focus: str, role: str) -> str:
    """Subject for a fresh (day-0) KCY cold-outreach email.

    service_focus in {"Peer Review", "Inspection", "Peer Review + Inspection"}.
    """
    project = (project or "Your Project").strip()
    if "Peer Review" in service_focus and not _role_is_gc_or_cm(role):
        return f"Expedited Peer Review & Third-Party Inspection Services for {project} | KCY Engineer PLLC"
    return f"Third-Party Inspection Services for {project} | KCY Engineer PLLC"


def followup_subject(original_subject: str, has_peer_review: bool,
                     company: str = "", project: str = "") -> str:
    """Subject for a KCY follow-up. Mirrors send_cw_followups._followup_subject."""
    m = re.search(r"Services for (.+?)\s*\|", original_subject or "")
    project_short = m.group(1).strip() if m else ""
    if not project_short:
        project_short = project or (f"{company} Projects" if company else "Your Project")

    if has_peer_review:
        return f"Following Up — Peer Review & Inspection Services for {project_short} | KCY Engineer"
    return f"Following Up — Inspection Services for {project_short} | KCY Engineer"


# ── Cold-outreach body generator ──────────────────────────────────────────────
def cold_body(contact_name: str, company: str, role: str, project_name: str,
              service_focus: str = "Inspection") -> str:
    """KCY cold-outreach email body. Role-aware, no signature, no ellipses."""
    first = _first_name(contact_name)
    salutation = f"Hi {first}," if first else "Hi,"
    peer_review_focus = "Peer Review" in service_focus and not _role_is_gc_or_cm(role)

    if _role_is_gc_or_cm(role):
        parts = [
            salutation,
            "",
            f"I noticed {company} is working on {project_name} and wanted to "
            f"take a moment to introduce KCY Engineer PLLC as a potential "
            f"resource for your Third-Party Inspection needs.",
            "",
            f"KCY Engineer PLLC is a licensed engineering firm providing "
            f"{_inspection_territory_phrase()}. A few reasons {company} may "
            f"find us a strong fit for this project:",
            "",
            BULLET_EXPERTISE,
            "",
            BULLET_SCHEDULING,
            "",
            BULLET_BILLING_INSPECTION,
            "",
            "We are not submitting a formal proposal at this stage, but if you "
            "are still finalizing your inspection vendor list for this project, "
            "we would welcome the opportunity to provide a competitive quote.",
            "",
            "Are you open to a quick 5-minute call or a brief capability overview?",
        ]

    elif _role_is_developer_or_owner(role):
        if peer_review_focus:
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce "
                f"KCY Engineer PLLC as a resource for {company}'s Expedited "
                f"Peer Review and Third-Party Inspection needs.",
                "",
                f"KCY is a licensed engineering firm providing "
                f"{_peer_review_territory_phrase()}, along with "
                f"{_inspection_territory_phrase()}. At this stage of the "
                f"project, our expedited peer review services can help identify "
                f"and resolve code issues before submission — saving time and "
                f"avoiding costly revision cycles. A few highlights:",
                "",
                BULLET_EXPERTISE,
                "",
                BULLET_PEER_REVIEW,
                "",
                BULLET_BILLING_INSPECTION,
                "",
                f"We are not submitting a formal proposal at this stage, but if "
                f"you would like to learn more about how KCY can support "
                f"{project_name} through peer review or later inspections, we "
                f"would welcome the conversation.",
                "",
                "Are you open to a quick 5-minute call?",
            ]
        else:
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce "
                f"KCY Engineer PLLC as a resource for {company}'s Third-Party "
                f"Inspection and Expedited Peer Review needs.",
                "",
                f"KCY is a licensed engineering firm providing "
                f"{_inspection_territory_phrase()}, along with "
                f"{_peer_review_territory_phrase()}. A few highlights:",
                "",
                BULLET_EXPERTISE,
                "",
                BULLET_SCHEDULING,
                "",
                BULLET_BILLING_INSPECTION,
                "",
                "Also, as a quick note — KCY offers Expedited Peer Review for "
                "jurisdictions nationwide. If your team needs pre-submission "
                "code review or independent peer review, we would be glad to assist.",
                "",
                f"We are not submitting a formal proposal at this stage, but if "
                f"you would like to learn more about our services for "
                f"{project_name}, we would welcome the conversation.",
                "",
                "Are you open to a quick 5-minute call?",
            ]

    elif _role_is_architect(role):
        if peer_review_focus:
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce "
                f"KCY Engineer PLLC. We frequently collaborate with architects "
                f"on Expedited Peer Review — particularly at the design stage "
                f"when code issues are most efficiently resolved.",
                "",
                f"KCY is a licensed engineering firm providing "
                f"{_peer_review_territory_phrase()}, along with "
                f"{_inspection_territory_phrase()}. A few highlights relevant "
                f"to {company}:",
                "",
                BULLET_EXPERTISE,
                "",
                BULLET_PEER_REVIEW,
                "",
                BULLET_BILLING_INSPECTION,
                "",
                f"We are not submitting a formal proposal at this stage, but "
                f"would welcome the opportunity to discuss how KCY can support "
                f"{project_name} during design and into construction.",
                "",
                "Are you open to a quick 5-minute call?",
            ]
        else:
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce "
                f"KCY Engineer PLLC. We often collaborate with architects on "
                f"Expedited Peer Review and third-party code compliance work.",
                "",
                f"KCY is a licensed engineering firm providing "
                f"{_peer_review_territory_phrase()}, along with "
                f"{_inspection_territory_phrase()}. A few highlights relevant "
                f"to {company}:",
                "",
                BULLET_EXPERTISE,
                "",
                BULLET_SCHEDULING,
                "",
                BULLET_BILLING_INSPECTION,
                "",
                "We also offer Expedited Peer Review services that can help "
                "identify code issues before submission — reducing revision "
                "cycles and protecting your project schedule.",
                "",
                f"We are not submitting a formal proposal at this stage, but "
                f"would welcome the opportunity to discuss how KCY can support "
                f"{project_name}.",
                "",
                "Are you open to a quick 5-minute call?",
            ]

    else:
        # Conservative default — pick by service_focus
        if peer_review_focus:
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce "
                f"KCY Engineer PLLC as a resource for Expedited Peer Review "
                f"and Third-Party Inspection needs.",
                "",
                f"KCY is a licensed engineering firm providing "
                f"{_peer_review_territory_phrase()}, along with "
                f"{_inspection_territory_phrase()}. A few reasons we may be a "
                f"strong fit:",
                "",
                BULLET_EXPERTISE,
                "",
                BULLET_PEER_REVIEW,
                "",
                BULLET_BILLING_INSPECTION,
                "",
                "We are not submitting a formal proposal at this stage, but if "
                "you are exploring peer review or inspection resources for this "
                "project, we would welcome a brief conversation.",
                "",
                "Are you open to a quick 5-minute call?",
            ]
        else:
            parts = [
                salutation,
                "",
                f"I came across {project_name} and wanted to briefly introduce "
                f"KCY Engineer PLLC as a potential resource for Third-Party "
                f"Inspection needs.",
                "",
                f"KCY is a licensed engineering firm providing "
                f"{_inspection_territory_phrase()}. A few reasons we may be a "
                f"strong fit:",
                "",
                BULLET_EXPERTISE,
                "",
                BULLET_SCHEDULING,
                "",
                BULLET_BILLING_INSPECTION,
                "",
                "We are not submitting a formal proposal at this stage, but if "
                "you are exploring inspection vendors for this project, we "
                "would welcome a brief conversation.",
                "",
                "Are you open to a quick 5-minute call?",
            ]

    return "\n".join(parts)


# ── Follow-up body generators ─────────────────────────────────────────────────
def followup_body_inspection(first: str, company: str, project: str) -> str:
    """KCY follow-up for inspection-only outreach (GC/CM)."""
    salutation = f"Hi {first}," if first else "Hi,"
    if project:
        intro = (
            f"Just following up on my earlier email regarding Third-Party "
            f"Inspection services for {project}."
        )
        support = (
            f"I wanted to make sure it reached you. KCY Engineer PLLC provides "
            f"{_inspection_territory_phrase()}, and we would welcome the chance "
            f"to support {company} on this project."
        )
    else:
        intro = (
            "Just following up on my earlier email regarding Third-Party "
            "Inspection services for your projects."
        )
        support = (
            f"I wanted to make sure it reached you. KCY Engineer PLLC provides "
            f"{_inspection_territory_phrase()}, and we would welcome the chance "
            f"to support {company}."
        )
    return "\n".join([
        salutation,
        "",
        intro,
        "",
        support,
        "",
        "As a quick reminder:",
        "",
        "- " + BULLET_EXPERTISE,
        "",
        "- " + BULLET_SCHEDULING,
        "",
        "- " + BULLET_BILLING_INSPECTION,
        "",
        "Would you be open to a quick 5-minute call to discuss how we can help?",
    ])


def followup_body_peer_review(first: str, company: str, project: str) -> str:
    """KCY follow-up for peer review + inspection outreach (Dev/Owner/Architect)."""
    salutation = f"Hi {first}," if first else "Hi,"
    if project:
        intro = (
            f"Just following up on my earlier email regarding Expedited Peer "
            f"Review and Third-Party Inspection services for {project}."
        )
    else:
        intro = (
            "Just following up on my earlier email regarding Expedited Peer "
            "Review and Third-Party Inspection services for your projects."
        )
    return "\n".join([
        salutation,
        "",
        intro,
        "",
        f"I wanted to make sure it reached you. KCY Engineer PLLC specializes "
        f"in {_peer_review_territory_phrase()} and {_inspection_territory_phrase()}, "
        f"and we would welcome the chance to support {company}.",
        "",
        "As a quick reminder:",
        "",
        "- " + BULLET_EXPERTISE,
        "",
        "- " + BULLET_PEER_REVIEW,
        "",
        "- " + BULLET_BILLING_INSPECTION,
        "",
        "Would you be open to a quick 5-minute call to discuss?",
    ])
