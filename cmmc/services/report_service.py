"""Assessment report generation — PDF and CSV formats."""

import csv
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from cmmc.errors import NotFoundError
from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.finding import Finding


def generate_assessment_report(
    db: Session, assessment_id: str, *, fmt: str = "csv"
) -> bytes:
    """Generate an assessment report in the requested format.

    Args:
        db: Database session.
        assessment_id: Assessment to report on.
        fmt: ``"csv"`` or ``"pdf"``.

    Returns:
        Report bytes.

    Raises:
        NotFoundError: Assessment not found.
        ValueError: Unsupported format.
    """
    if fmt not in ("csv", "pdf"):
        raise ValueError(f"Unsupported format: {fmt}")

    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise NotFoundError("Assessment not found")

    data = _gather_data(db, assessment)

    if fmt == "csv":
        return _render_csv(data)
    return _render_pdf(data)


# ---------------------------------------------------------------------------
# Data gathering
# ---------------------------------------------------------------------------


def _gather_data(db: Session, assessment: Assessment) -> dict:
    """Collect all data needed for the report."""
    # Practices with domain info
    rows = (
        db.query(AssessmentPractice, CMMCPractice)
        .join(CMMCPractice, AssessmentPractice.practice_id == CMMCPractice.practice_id)
        .filter(AssessmentPractice.assessment_id == assessment.id)
        .order_by(CMMCPractice.practice_id)
        .all()
    )

    # Domain lookup
    domain_ids = {cp.domain_ref for _, cp in rows}
    domains = db.query(CMMCDomain).filter(CMMCDomain.domain_id.in_(domain_ids)).all() if domain_ids else []
    domain_map = {d.domain_id: d.name for d in domains}

    practices = []
    for ap, cp in rows:
        practices.append({
            "practice_id": cp.practice_id,
            "domain": domain_map.get(cp.domain_ref, cp.domain_ref),
            "domain_id": cp.domain_ref,
            "level": cp.level,
            "title": cp.title,
            "status": ap.status,
            "notes": ap.assessor_notes or "",
        })

    # Findings
    findings = (
        db.query(Finding)
        .filter_by(assessment_id=assessment.id)
        .order_by(Finding.severity, Finding.title)
        .all()
    )

    # Domain compliance summary
    by_domain: dict[str, dict] = {}
    for p in practices:
        d = p["domain_id"]
        if d not in by_domain:
            by_domain[d] = {"name": p["domain"], "met": 0, "total": 0}
        if p["status"] != "not_applicable":
            by_domain[d]["total"] += 1
            if p["status"] == "met":
                by_domain[d]["met"] += 1

    return {
        "assessment": assessment,
        "practices": practices,
        "findings": findings,
        "domain_summary": by_domain,
    }


# ---------------------------------------------------------------------------
# CSV renderer
# ---------------------------------------------------------------------------


def _render_csv(data: dict) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)

    assessment = data["assessment"]

    # Executive summary section
    writer.writerow(["Assessment Report"])
    writer.writerow(["Title", assessment.title])
    writer.writerow(["Status", assessment.status])
    writer.writerow(["Target Level", assessment.target_level])
    writer.writerow(["Type", assessment.assessment_type])
    writer.writerow(["SPRS Score", assessment.sprs_score or "N/A"])
    writer.writerow(["Overall Score (%)", assessment.overall_score or "N/A"])
    writer.writerow(["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    writer.writerow([])

    # Domain summary
    writer.writerow(["Domain Compliance Summary"])
    writer.writerow(["Domain", "Met", "Total", "Percentage"])
    for did in sorted(data["domain_summary"]):
        ds = data["domain_summary"][did]
        pct = round(ds["met"] / ds["total"] * 100, 1) if ds["total"] else 0.0
        writer.writerow([f"{did} — {ds['name']}", ds["met"], ds["total"], f"{pct}%"])
    writer.writerow([])

    # Practice details
    writer.writerow(["Practice Details"])
    writer.writerow(["Practice ID", "Domain", "Level", "Title", "Status", "Notes"])
    for p in data["practices"]:
        writer.writerow([
            p["practice_id"],
            p["domain"],
            p["level"],
            p["title"],
            p["status"],
            p["notes"],
        ])
    writer.writerow([])

    # Findings
    writer.writerow(["Findings"])
    writer.writerow(["Title", "Type", "Severity", "Status", "Practice"])
    for f in data["findings"]:
        writer.writerow([
            f.title,
            f.finding_type,
            f.severity,
            f.status,
            f.practice_id or "",
        ])

    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# PDF renderer
# ---------------------------------------------------------------------------


def _render_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("Heading", parent=styles["Heading1"], fontSize=16)
    subheading = ParagraphStyle("Sub", parent=styles["Heading2"], fontSize=12)
    body = styles["BodyText"]

    elements: list = []
    assessment = data["assessment"]

    # Title
    elements.append(Paragraph("CMMC Assessment Report", heading))
    elements.append(Spacer(1, 12))

    # Executive summary
    elements.append(Paragraph("Executive Summary", subheading))
    summary_data = [
        ["Title", assessment.title],
        ["Status", assessment.status.replace("_", " ").title()],
        ["Target Level", str(assessment.target_level)],
        ["Type", assessment.assessment_type.replace("_", " ").title()],
        ["SPRS Score", str(assessment.sprs_score) if assessment.sprs_score is not None else "N/A"],
        ["Overall Compliance", f"{assessment.overall_score}%" if assessment.overall_score is not None else "N/A"],
        ["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
    ]
    t = Table(summary_data, colWidths=[2 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 16))

    # Domain compliance
    elements.append(Paragraph("Domain Compliance", subheading))
    domain_rows = [["Domain", "Met", "Total", "%"]]
    for did in sorted(data["domain_summary"]):
        ds = data["domain_summary"][did]
        pct = round(ds["met"] / ds["total"] * 100, 1) if ds["total"] else 0.0
        domain_rows.append([f"{did} — {ds['name']}", str(ds["met"]), str(ds["total"]), f"{pct}%"])

    if len(domain_rows) > 1:
        dt = Table(domain_rows, colWidths=[3 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(dt)
    elements.append(Spacer(1, 16))

    # Practice details
    elements.append(Paragraph("Practice Details", subheading))
    practice_rows = [["Practice", "Domain", "Lvl", "Status", "Title"]]
    for p in data["practices"]:
        practice_rows.append([
            p["practice_id"],
            p["domain_id"],
            str(p["level"]),
            p["status"].replace("_", " ").title(),
            Paragraph(p["title"], body) if len(p["title"]) > 40 else p["title"],
        ])

    pt = Table(practice_rows, colWidths=[1.3 * inch, 0.6 * inch, 0.4 * inch, 1 * inch, 3.1 * inch])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(pt)
    elements.append(Spacer(1, 16))

    # Findings
    if data["findings"]:
        elements.append(Paragraph("Findings", subheading))
        finding_rows = [["Title", "Type", "Severity", "Status"]]
        for f in data["findings"]:
            finding_rows.append([
                Paragraph(f.title, body) if len(f.title) > 30 else f.title,
                f.finding_type.replace("_", " ").title(),
                f.severity.title(),
                f.status.title(),
            ])

        ft = Table(finding_rows, colWidths=[2.8 * inch, 1.3 * inch, 1 * inch, 1 * inch])
        ft.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(ft)

    doc.build(elements)
    return buf.getvalue()
