"""Dashboard data aggregation service."""

from collections import Counter

from sqlalchemy.orm import Session

from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.finding import Finding


def get_compliance_summary(db: Session, org_id: str) -> dict:
    """Overall compliance % for the org's most recent completed assessment per level.

    Returns ``{level_1: float|None, level_2: float|None, level_3: float|None}``.
    """
    result: dict[str, float | None] = {
        "level_1": None,
        "level_2": None,
        "level_3": None,
    }

    for level in (1, 2, 3):
        assessment = (
            db.query(Assessment)
            .filter_by(org_id=org_id, status="completed", target_level=level)
            .order_by(Assessment.created_at.desc())
            .first()
        )
        if not assessment:
            continue

        practices = (
            db.query(AssessmentPractice)
            .filter_by(assessment_id=assessment.id)
            .all()
        )
        scorable = [p for p in practices if p.status != "not_applicable"]
        if not scorable:
            continue

        met = sum(1 for p in scorable if p.status == "met")
        result[f"level_{level}"] = round(met / len(scorable) * 100, 1)

    return result


def get_domain_compliance(db: Session, assessment_id: str) -> list[dict]:
    """Per-domain compliance scores for a specific assessment.

    Returns ``[{domain_id, domain_name, met, total, percentage}, ...]``.
    """
    practices = (
        db.query(AssessmentPractice, CMMCPractice)
        .join(CMMCPractice, AssessmentPractice.practice_id == CMMCPractice.practice_id)
        .filter(AssessmentPractice.assessment_id == assessment_id)
        .all()
    )

    if not practices:
        return []

    # Build domain lookup
    domain_ids = {cp.domain_ref for _, cp in practices}
    domains = db.query(CMMCDomain).filter(CMMCDomain.domain_id.in_(domain_ids)).all()
    domain_map = {d.domain_id: d.name for d in domains}

    # Group by domain
    by_domain: dict[str, list[AssessmentPractice]] = {}
    for ap, cp in practices:
        by_domain.setdefault(cp.domain_ref, []).append(ap)

    result = []
    for domain_id in sorted(by_domain):
        evals = by_domain[domain_id]
        scorable = [e for e in evals if e.status != "not_applicable"]
        total = len(scorable)
        met = sum(1 for e in scorable if e.status == "met")
        result.append({
            "domain_id": domain_id,
            "domain_name": domain_map.get(domain_id, domain_id),
            "met": met,
            "total": total,
            "percentage": round(met / total * 100, 1) if total else 0.0,
        })

    return result


def get_sprs_summary(db: Session, org_id: str) -> dict:
    """Current + historical SPRS scores for an org.

    Returns ``{current: int|None, history: [{assessment_id, title, sprs_score, date}, ...]}``.
    """
    assessments = (
        db.query(Assessment)
        .filter(Assessment.org_id == org_id, Assessment.sprs_score.isnot(None))
        .order_by(Assessment.created_at.desc())
        .all()
    )

    if not assessments:
        return {"current": None, "history": []}

    history = [
        {
            "assessment_id": a.id,
            "title": a.title,
            "sprs_score": a.sprs_score,
            "date": a.created_at.isoformat() if a.created_at else None,
        }
        for a in assessments
    ]

    return {
        "current": assessments[0].sprs_score,
        "history": history,
    }


def get_assessment_timeline(
    db: Session, org_id: str, *, limit: int = 10
) -> list[dict]:
    """Recent assessments for an org, newest first.

    Returns list of assessment summaries.
    """
    assessments = (
        db.query(Assessment)
        .filter_by(org_id=org_id)
        .order_by(Assessment.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": a.id,
            "title": a.title,
            "status": a.status,
            "target_level": a.target_level,
            "assessment_type": a.assessment_type,
            "overall_score": a.overall_score,
            "sprs_score": a.sprs_score,
            "created_at": a.created_at.isoformat() if a.created_at else None,
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
        }
        for a in assessments
    ]


def get_findings_summary(db: Session, assessment_id: str) -> dict:
    """Findings counts by severity and status.

    Returns ``{total, by_severity: {sev: count}, by_status: {status: count}}``.
    """
    findings = db.query(Finding).filter_by(assessment_id=assessment_id).all()

    if not findings:
        return {"total": 0, "by_severity": {}, "by_status": {}}

    by_severity = dict(Counter(f.severity for f in findings))
    by_status = dict(Counter(f.status for f in findings))

    return {
        "total": len(findings),
        "by_severity": by_severity,
        "by_status": by_status,
    }
