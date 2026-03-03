"""Seed CMMC reference data from YAML files into the database."""

import logging
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from cmmc.models import CMMCDomain, CMMCLevel, CMMCPractice

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cmmc"


def seed_all(db: Session) -> dict[str, int]:
    """Seed all CMMC reference data. Returns counts of upserted records."""
    counts: dict[str, int] = {}
    counts["domains"] = _seed_domains(db)
    counts["levels"] = _seed_levels(db)
    counts["practices"] = _seed_practices(db)
    db.commit()
    logger.info("Seed complete: %s", counts)
    return counts


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
