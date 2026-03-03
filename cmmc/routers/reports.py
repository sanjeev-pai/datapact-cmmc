"""Report API — assessment reports (PDF/CSV) and SPRS reports."""

import csv
import io
from enum import Enum

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from cmmc.database import get_db
from cmmc.dependencies.auth import get_current_user
from cmmc.errors import NotFoundError
from cmmc.models.user import User
from cmmc.services.dashboard_service import get_sprs_summary
from cmmc.services.report_service import generate_assessment_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportFormat(str, Enum):
    csv = "csv"
    pdf = "pdf"


# ---------------------------------------------------------------------------
# GET /assessment/{assessment_id}?format=csv|pdf
# ---------------------------------------------------------------------------

@router.get("/assessment/{assessment_id}")
def assessment_report(
    assessment_id: str,
    format: ReportFormat = Query(ReportFormat.csv, alias="format"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download an assessment report in CSV or PDF format."""
    try:
        data = generate_assessment_report(db, assessment_id, fmt=format.value)
    except NotFoundError:
        return Response(status_code=404, content='{"detail":"Assessment not found"}',
                        media_type="application/json")

    if format == ReportFormat.pdf:
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="assessment-{assessment_id}.pdf"',
            },
        )

    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="assessment-{assessment_id}.csv"',
        },
    )


# ---------------------------------------------------------------------------
# GET /sprs/{org_id}
# ---------------------------------------------------------------------------

@router.get("/sprs/{org_id}")
def sprs_report(
    org_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download SPRS score history for an organization as CSV."""
    summary = get_sprs_summary(db, org_id)

    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(["SPRS Score Report"])
    writer.writerow(["Organization ID", org_id])
    writer.writerow(["Current SPRS Score", summary["current"] or "N/A"])
    writer.writerow([])
    writer.writerow(["Assessment ID", "Title", "SPRS Score", "Date"])
    for entry in summary["history"]:
        writer.writerow([
            entry["assessment_id"],
            entry["title"],
            entry["sprs_score"],
            entry["date"] or "",
        ])

    return Response(
        content=buf.getvalue().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="sprs-{org_id}.csv"',
        },
    )
