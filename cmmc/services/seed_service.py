"""Seed CMMC reference data from YAML files into the database."""

import logging
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from cmmc.models import CMMCDomain, CMMCLevel, CMMCPractice
from cmmc.models.assessment import Assessment
from cmmc.models.organization import Organization
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import hash_password

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cmmc"


def seed_all(db: Session) -> dict[str, int]:
    """Seed all CMMC reference data. Returns counts of upserted records."""
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
