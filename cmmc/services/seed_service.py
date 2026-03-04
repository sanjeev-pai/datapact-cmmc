"""Seed CMMC reference data from YAML files into the database."""

import logging
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from cmmc.models import CMMCDomain, CMMCLevel, CMMCPractice
from cmmc.models.assessment import Assessment, AssessmentPractice
from cmmc.models.evidence import Evidence
from cmmc.models.finding import Finding
from cmmc.models.organization import Organization
from cmmc.models.poam import POAM, POAMItem
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import hash_password

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cmmc"


def seed_all(db: Session, *, seed_demo: bool = True) -> dict[str, int]:
    """Seed all CMMC reference data. Returns counts of upserted records.

    Args:
        db: Database session.
        seed_demo: If True, also load demo assessment data (evaluations, findings, POAMs)
                   from demo_assessment.yaml.
    """
    counts: dict[str, int] = {}
    counts["roles"] = _seed_roles(db)
    counts["users"] = _seed_users(db)
    counts["domains"] = _seed_domains(db)
    counts["levels"] = _seed_levels(db)
    counts["practices"] = _seed_practices(db)
    db.commit()
    counts["organizations"] = _seed_organizations(db)
    counts["assessments"] = _seed_assessments(db)
    db.commit()
    counts["evidence"] = _seed_evidence(db)
    db.commit()
    if seed_demo:
        demo = _load_yaml("demo_assessment.yaml")
        counts["practice_evaluations"] = _seed_practice_evaluations(db, demo)
        counts["findings"] = _seed_findings(db, demo)
        db.commit()
        counts["poams"] = _seed_poams(db, demo)
        db.commit()
    logger.info("Seed complete: %s", counts)
    return counts


DEFAULT_ROLES = [
    "system_admin",
    "org_admin",
    "compliance_officer",
    "assessor",
    "c3pao_lead",
    "viewer",
]


def _seed_roles(db: Session) -> int:
    count = 0
    for role_name in DEFAULT_ROLES:
        existing = db.query(Role).filter_by(name=role_name).first()
        if not existing:
            db.add(Role(name=role_name))
        count += 1
    db.flush()
    return count


SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@datapact.local",
        "password": "admin123!",
        "roles": ["system_admin", "org_admin"],
    },
    {
        "username": "jwchandna",
        "email": "jwchandna@datapact.local",
        "password": "jwchandna_ciso_135$$$",
        "roles": ["system_admin", "org_admin"],
    },
]


def _seed_users(db: Session) -> int:
    count = 0
    for item in SEED_USERS:
        existing = db.query(User).filter_by(username=item["username"]).first()
        if existing:
            count += 1
            continue
        user = User(
            username=item["username"],
            email=item["email"],
            password_hash=hash_password(item["password"]),
            is_active=True,
        )
        db.add(user)
        db.flush()
        for role_name in item["roles"]:
            role = db.query(Role).filter_by(name=role_name).first()
            if role:
                db.add(UserRole(user_id=user.id, role_id=role.id))
        count += 1
    db.flush()
    return count


def _seed_domains(db: Session) -> int:
    data = _load_yaml("domains.yaml")
    count = 0
    for item in data.get("domains", []):
        existing = db.query(CMMCDomain).filter_by(domain_id=item["id"]).first()
        if existing:
            existing.name = item["name"]
            existing.description = item.get("description", "")
        else:
            db.add(
                CMMCDomain(
                    domain_id=item["id"],
                    name=item["name"],
                    description=item.get("description", ""),
                )
            )
        count += 1
    db.flush()
    return count


def _seed_levels(db: Session) -> int:
    levels = [
        {"level": 1, "name": "Foundational", "assessment_type": "self",
         "description": "Basic safeguarding of FCI (FAR 52.204-21). 17 practices."},
        {"level": 2, "name": "Advanced", "assessment_type": "third_party",
         "description": "Protection of CUI (NIST SP 800-171 Rev 2). 110 practices."},
        {"level": 3, "name": "Expert", "assessment_type": "government",
         "description": "Enhanced protection of CUI (NIST SP 800-172). 130+ practices."},
    ]
    count = 0
    for item in levels:
        existing = db.query(CMMCLevel).filter_by(level=item["level"]).first()
        if existing:
            existing.name = item["name"]
            existing.assessment_type = item["assessment_type"]
            existing.description = item["description"]
        else:
            db.add(CMMCLevel(**item))
        count += 1
    db.flush()
    return count


def _seed_practices(db: Session) -> int:
    count = 0
    for filename in ["level1_practices.yaml", "level2_practices.yaml", "level3_practices.yaml"]:
        data = _load_yaml(filename)
        for item in data.get("practices", []):
            existing = (
                db.query(CMMCPractice)
                .filter_by(practice_id=item["practice_id"])
                .first()
            )
            if existing:
                existing.domain_ref = item["domain"]
                existing.level = item["level"]
                existing.title = item["title"]
                existing.description = item.get("description", "")
                existing.nist_refs = item.get("nist_refs")
                existing.assessment_objectives = item.get("assessment_objectives")
                existing.evidence_requirements = item.get("evidence_requirements")
            else:
                db.add(
                    CMMCPractice(
                        practice_id=item["practice_id"],
                        domain_ref=item["domain"],
                        level=item["level"],
                        title=item["title"],
                        description=item.get("description", ""),
                        nist_refs=item.get("nist_refs"),
                        assessment_objectives=item.get("assessment_objectives"),
                        evidence_requirements=item.get("evidence_requirements"),
                    )
                )
            count += 1
    db.flush()
    return count


SEED_ORGS = [
    {
        "name": "Mrisan",
        "cage_code": "0MRS1",
        "duns_number": "000000001",
        "target_level": 3,
    },
    {
        "name": "Acme Defense Corp",
        "cage_code": "1ABC2",
        "duns_number": "123456789",
        "target_level": 2,
    },
    {
        "name": "Pinnacle Aero Systems",
        "cage_code": "3DEF4",
        "duns_number": "987654321",
        "target_level": 3,
    },
]

# Map seed users to their organizations
SEED_USER_ORGS = {
    "admin": "Mrisan",
    "jwchandna": "Mrisan",
}

SEED_ASSESSMENTS = [
    {
        "org_name": "Acme Defense Corp",
        "title": "Acme L1 Self-Assessment (FY25)",
        "target_level": 1,
        "assessment_type": "self",
        "status": "in_progress",
    },
    {
        "org_name": "Acme Defense Corp",
        "title": "Acme L2 C3PAO Assessment (FY25)",
        "target_level": 2,
        "assessment_type": "third_party",
        "status": "draft",
    },
    {
        "org_name": "Pinnacle Aero Systems",
        "title": "Pinnacle L2 Self-Assessment (FY25)",
        "target_level": 2,
        "assessment_type": "self",
        "status": "completed",
    },
    {
        "org_name": "Pinnacle Aero Systems",
        "title": "Pinnacle L3 DIBCAC Assessment (FY26)",
        "target_level": 3,
        "assessment_type": "government",
        "status": "draft",
    },
]


def _seed_organizations(db: Session) -> int:
    count = 0
    for item in SEED_ORGS:
        existing = db.query(Organization).filter_by(name=item["name"]).first()
        if existing:
            count += 1
            continue
        db.add(Organization(**item))
        count += 1
    db.flush()

    # Assign users to their orgs
    for username, org_name in SEED_USER_ORGS.items():
        user = db.query(User).filter_by(username=username).first()
        org = db.query(Organization).filter_by(name=org_name).first()
        if user and org and user.org_id != org.id:
            user.org_id = org.id
    db.flush()

    return count


def _seed_assessments(db: Session) -> int:
    from cmmc.services.assessment_service import create_assessment

    count = 0
    for item in SEED_ASSESSMENTS:
        org = db.query(Organization).filter_by(name=item["org_name"]).first()
        if not org:
            logger.warning("Org not found for assessment seed: %s", item["org_name"])
            continue
        existing = (
            db.query(Assessment)
            .filter_by(org_id=org.id, title=item["title"])
            .first()
        )
        if existing:
            count += 1
            continue
        assessment = create_assessment(
            db,
            org_id=org.id,
            title=item["title"],
            target_level=item["target_level"],
            assessment_type=item["assessment_type"],
        )
        # Advance status beyond draft if needed
        if item["status"] in ("in_progress", "under_review", "completed"):
            assessment.status = "in_progress"
            assessment.started_at = assessment.created_at
        if item["status"] in ("under_review", "completed"):
            assessment.status = "under_review"
        if item["status"] == "completed":
            assessment.status = "completed"
            assessment.completed_at = assessment.updated_at
        count += 1
    db.flush()
    return count


SEED_EVIDENCE = [
    # Evidence for "Acme L1 Self-Assessment (FY25)" — in_progress
    {
        "assessment_title": "Acme L1 Self-Assessment (FY25)",
        "practice_id": "AC.L1-3.1.1",
        "title": "Access Control Policy v3.2",
        "description": "Corporate access control policy covering user provisioning and deprovisioning.",
        "file_name": "access_control_policy_v3.2.pdf",
        "file_size": 245_760,
        "mime_type": "application/pdf",
        "review_status": "accepted",
    },
    {
        "assessment_title": "Acme L1 Self-Assessment (FY25)",
        "practice_id": "AC.L1-3.1.1",
        "title": "Active Directory User Audit - Feb 2026",
        "description": "Screenshot showing quarterly AD user access review results.",
        "file_name": "ad_user_audit_feb2026.png",
        "file_size": 189_440,
        "mime_type": "image/png",
        "review_status": "pending",
    },
    {
        "assessment_title": "Acme L1 Self-Assessment (FY25)",
        "practice_id": "AC.L1-3.1.2",
        "title": "VPN Configuration Export",
        "description": "Network configuration showing transaction and function restrictions.",
        "file_name": "vpn_config_export.xlsx",
        "file_size": 87_040,
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "review_status": "pending",
    },
    {
        "assessment_title": "Acme L1 Self-Assessment (FY25)",
        "practice_id": "IA.L1-3.5.1",
        "title": "MFA Enrollment Report",
        "description": "Report showing 98% MFA enrollment across all user accounts.",
        "file_name": "mfa_enrollment_report.pdf",
        "file_size": 156_672,
        "mime_type": "application/pdf",
        "review_status": "accepted",
    },
    {
        "assessment_title": "Acme L1 Self-Assessment (FY25)",
        "practice_id": "IA.L1-3.5.2",
        "title": "Password Policy Screenshot",
        "description": "Azure AD password policy settings showing complexity requirements.",
        "file_name": "password_policy_aad.png",
        "file_size": 312_320,
        "mime_type": "image/png",
        "review_status": "rejected",
    },
    # Evidence for "Pinnacle L2 Self-Assessment (FY25)" — completed
    {
        "assessment_title": "Pinnacle L2 Self-Assessment (FY25)",
        "practice_id": "AC.L1-3.1.1",
        "title": "System Security Plan - Access Control",
        "description": "SSP section covering access control policies and procedures.",
        "file_name": "ssp_access_control.docx",
        "file_size": 524_288,
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "review_status": "accepted",
    },
    {
        "assessment_title": "Pinnacle L2 Self-Assessment (FY25)",
        "practice_id": "AC.L2-3.1.3",
        "title": "CUI Data Flow Diagram",
        "description": "Network diagram showing CUI flow boundaries and access points.",
        "file_name": "cui_data_flow_v2.pdf",
        "file_size": 1_048_576,
        "mime_type": "application/pdf",
        "review_status": "accepted",
    },
    {
        "assessment_title": "Pinnacle L2 Self-Assessment (FY25)",
        "practice_id": "SC.L1-3.13.1",
        "title": "Network Boundary Protection Config",
        "description": "Firewall rules and IDS/IPS configuration for CUI boundary monitoring.",
        "file_name": "firewall_config_export.json",
        "file_size": 42_000,
        "mime_type": "application/json",
        "review_status": "accepted",
    },
]


def _seed_evidence(db: Session) -> int:
    count = 0
    for item in SEED_EVIDENCE:
        # Find the assessment
        assessment = db.query(Assessment).filter_by(title=item["assessment_title"]).first()
        if not assessment:
            logger.warning("Assessment not found for evidence seed: %s", item["assessment_title"])
            continue

        # Find the assessment practice
        ap = (
            db.query(AssessmentPractice)
            .filter_by(assessment_id=assessment.id, practice_id=item["practice_id"])
            .first()
        )
        if not ap:
            logger.warning(
                "AssessmentPractice not found: %s / %s",
                item["assessment_title"],
                item["practice_id"],
            )
            continue

        # Skip if evidence with same title already exists for this practice
        existing = (
            db.query(Evidence)
            .filter_by(assessment_practice_id=ap.id, title=item["title"])
            .first()
        )
        if existing:
            count += 1
            continue

        evidence = Evidence(
            assessment_practice_id=ap.id,
            title=item["title"],
            description=item.get("description"),
            file_name=item.get("file_name"),
            file_size=item.get("file_size"),
            mime_type=item.get("mime_type"),
            review_status=item.get("review_status", "pending"),
        )
        db.add(evidence)
        count += 1
    db.flush()
    return count


def _seed_practice_evaluations(db: Session, demo: dict) -> int:
    """Seed practice evaluation statuses from demo YAML data."""
    count = 0
    for group in demo.get("practice_evaluations", []):
        assessment = db.query(Assessment).filter_by(title=group["assessment_title"]).first()
        if not assessment:
            logger.warning("Assessment not found for eval seed: %s", group["assessment_title"])
            continue
        for ev in group.get("evaluations", []):
            ap = (
                db.query(AssessmentPractice)
                .filter_by(assessment_id=assessment.id, practice_id=ev["practice_id"])
                .first()
            )
            if not ap:
                logger.warning(
                    "AssessmentPractice not found: %s / %s",
                    group["assessment_title"],
                    ev["practice_id"],
                )
                continue
            ap.status = ev["status"]
            ap.score = ev.get("score")
            ap.assessor_notes = ev.get("assessor_notes")
            count += 1
    db.flush()
    return count


def _seed_findings(db: Session, demo: dict) -> int:
    """Seed findings from demo YAML data."""
    count = 0
    for group in demo.get("findings", []):
        assessment = db.query(Assessment).filter_by(title=group["assessment_title"]).first()
        if not assessment:
            logger.warning("Assessment not found for finding seed: %s", group["assessment_title"])
            continue
        for item in group.get("items", []):
            existing = (
                db.query(Finding)
                .filter_by(assessment_id=assessment.id, title=item["title"])
                .first()
            )
            if existing:
                count += 1
                continue
            db.add(
                Finding(
                    assessment_id=assessment.id,
                    practice_id=item.get("practice_id"),
                    finding_type=item["finding_type"],
                    severity=item["severity"],
                    title=item["title"],
                    description=item.get("description"),
                    status=item.get("status", "open"),
                )
            )
            count += 1
    db.flush()
    return count


def _seed_poams(db: Session, demo: dict) -> int:
    """Seed POAMs and their items from demo YAML data."""
    count = 0
    for poam_data in demo.get("poams", []):
        org = db.query(Organization).filter_by(name=poam_data["org_name"]).first()
        assessment = db.query(Assessment).filter_by(title=poam_data["assessment_title"]).first()
        if not org or not assessment:
            logger.warning(
                "Org/assessment not found for POAM seed: %s / %s",
                poam_data["org_name"],
                poam_data["assessment_title"],
            )
            continue

        existing = db.query(POAM).filter_by(org_id=org.id, title=poam_data["title"]).first()
        if existing:
            count += 1
            continue

        poam = POAM(
            org_id=org.id,
            assessment_id=assessment.id,
            title=poam_data["title"],
            status=poam_data.get("status", "draft"),
        )
        db.add(poam)
        db.flush()

        for item in poam_data.get("items", []):
            # Optionally link to finding by title
            finding = None
            if item.get("finding_title"):
                finding = (
                    db.query(Finding)
                    .filter_by(assessment_id=assessment.id, title=item["finding_title"])
                    .first()
                )
            scheduled = None
            if item.get("scheduled_completion"):
                scheduled = date.fromisoformat(item["scheduled_completion"])
            actual = None
            if item.get("actual_completion"):
                actual = date.fromisoformat(item["actual_completion"])
            db.add(
                POAMItem(
                    poam_id=poam.id,
                    finding_id=finding.id if finding else None,
                    practice_id=item.get("practice_id"),
                    milestone=item.get("milestone"),
                    scheduled_completion=scheduled,
                    actual_completion=actual,
                    status=item.get("status", "open"),
                    resources_required=item.get("resources_required"),
                )
            )
        count += 1
    db.flush()
    return count


def _load_yaml(filename: str) -> dict:
    path = DATA_DIR / filename
    if not path.exists():
        logger.warning("Seed file not found: %s", path)
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


# CLI entry-point: python -m cmmc.services.seed_service
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from cmmc.database import SessionLocal

    db = SessionLocal()
    try:
        result = seed_all(db)
        print(f"Seeded: {result}")
    finally:
        db.close()
