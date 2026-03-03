"""SPRS score calculation based on NIST SP 800-171 DoD Assessment Methodology.

Baseline: 110 points.  For each requirement NOT met, deduct its weight (1, 3, or 5).
Minimum possible: -203.  Maximum: 110.
"""

from sqlalchemy.orm import Session

from cmmc.errors import NotFoundError
from cmmc.models.assessment import Assessment, AssessmentPractice

# ---------------------------------------------------------------------------
# NIST 800-171 Rev 2 requirement weights (109 scored requirements)
# 3.12.4 (System Security Plan) is excluded — prerequisite, not scored.
# Source: DoD Assessment Methodology v1.2.1
# ---------------------------------------------------------------------------

# fmt: off
SPRS_WEIGHTS: dict[str, int] = {
    # 5-point requirements (44)
    "3.1.1": 5, "3.1.2": 5, "3.1.12": 5, "3.1.13": 5,
    "3.1.16": 5, "3.1.17": 5, "3.1.18": 5,
    "3.2.1": 5, "3.2.2": 5,
    "3.3.1": 5, "3.3.5": 5,
    "3.4.1": 5, "3.4.2": 5, "3.4.5": 5, "3.4.6": 5, "3.4.7": 5, "3.4.8": 5,
    "3.5.1": 5, "3.5.2": 5, "3.5.3": 5, "3.5.10": 5,
    "3.6.1": 5, "3.6.2": 5,
    "3.7.2": 5, "3.7.5": 5,
    "3.8.3": 5, "3.8.7": 5,
    "3.9.2": 5,
    "3.10.1": 5, "3.10.2": 5,
    "3.11.2": 5,
    "3.12.1": 5, "3.12.3": 5,
    "3.13.1": 5, "3.13.2": 5, "3.13.5": 5, "3.13.6": 5,
    "3.13.11": 5, "3.13.15": 5,
    "3.14.1": 5, "3.14.2": 5, "3.14.3": 5, "3.14.4": 5, "3.14.6": 5,

    # 3-point requirements (14)
    "3.1.5": 3, "3.1.19": 3,
    "3.3.2": 3,
    "3.7.1": 3, "3.7.4": 3,
    "3.8.1": 3, "3.8.2": 3, "3.8.8": 3,
    "3.9.1": 3,
    "3.11.1": 3,
    "3.12.2": 3,
    "3.13.8": 3,
    "3.14.5": 3, "3.14.7": 3,

    # 1-point requirements (51)
    "3.1.3": 1, "3.1.4": 1, "3.1.6": 1, "3.1.7": 1, "3.1.8": 1,
    "3.1.9": 1, "3.1.10": 1, "3.1.11": 1, "3.1.14": 1, "3.1.15": 1,
    "3.1.20": 1, "3.1.21": 1, "3.1.22": 1,
    "3.2.3": 1,
    "3.3.3": 1, "3.3.4": 1, "3.3.6": 1, "3.3.7": 1, "3.3.8": 1, "3.3.9": 1,
    "3.4.3": 1, "3.4.4": 1, "3.4.9": 1,
    "3.5.4": 1, "3.5.5": 1, "3.5.6": 1, "3.5.7": 1, "3.5.8": 1,
    "3.5.9": 1, "3.5.11": 1,
    "3.6.3": 1,
    "3.7.3": 1, "3.7.6": 1,
    "3.8.4": 1, "3.8.5": 1, "3.8.6": 1, "3.8.9": 1,
    "3.10.3": 1, "3.10.4": 1, "3.10.5": 1, "3.10.6": 1,
    "3.11.3": 1,
    "3.13.3": 1, "3.13.4": 1, "3.13.7": 1, "3.13.9": 1, "3.13.10": 1,
    "3.13.12": 1, "3.13.13": 1, "3.13.14": 1, "3.13.16": 1,
}
# fmt: on

_SPRS_BASELINE = 110


def get_nist_ref(practice_id: str) -> str | None:
    """Extract the NIST 800-171 requirement number from a CMMC practice_id.

    E.g. ``"AC.L2-3.1.3"`` → ``"3.1.3"``, ``"SC.L1-3.13.11"`` → ``"3.13.11"``.
    Returns None if the format doesn't match.
    """
    parts = practice_id.split("-", 1)
    if len(parts) == 2:
        return parts[1]
    return None


def calculate_sprs_score(db: Session, assessment_id: str) -> int:
    """Compute SPRS score (-203 to 110) for an assessment.

    - Start at 110
    - For each practice that is NOT 'met' or 'not_applicable', subtract its weight
    - Practices with status 'not_applicable' are excluded (no deduction)
    - Unknown practices default to weight 1
    """
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise NotFoundError(f"Assessment {assessment_id} not found")

    practices = (
        db.query(AssessmentPractice)
        .filter_by(assessment_id=assessment_id)
        .all()
    )

    deductions = 0
    for ap in practices:
        if ap.status in ("met", "not_applicable"):
            continue

        nist_ref = get_nist_ref(ap.practice_id)
        weight = SPRS_WEIGHTS.get(nist_ref, 1) if nist_ref else 1
        deductions += weight

    return _SPRS_BASELINE - deductions


def calculate_overall_score(db: Session, assessment_id: str) -> float:
    """Compute overall compliance percentage (0.0–100.0).

    Percentage of scorable practices (excluding not_applicable) that are met.
    """
    assessment = db.query(Assessment).filter_by(id=assessment_id).first()
    if not assessment:
        raise NotFoundError(f"Assessment {assessment_id} not found")

    practices = (
        db.query(AssessmentPractice)
        .filter_by(assessment_id=assessment_id)
        .all()
    )

    scorable = [ap for ap in practices if ap.status != "not_applicable"]
    if not scorable:
        return 0.0

    met_count = sum(1 for ap in scorable if ap.status == "met")
    return round(met_count / len(scorable) * 100, 1)
