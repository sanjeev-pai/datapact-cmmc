"""Seed service tests."""

from cmmc.models import CMMCDomain, CMMCLevel, CMMCPractice
from cmmc.services.seed_service import seed_all


class TestSeedService:
    def test_seed_creates_domains(self, db):
        counts = seed_all(db)
        assert counts["domains"] == 14
        assert db.query(CMMCDomain).count() == 14

    def test_seed_creates_levels(self, db):
        counts = seed_all(db)
        assert counts["levels"] == 3
        assert db.query(CMMCLevel).count() == 3

    def test_seed_creates_practices(self, db):
        counts = seed_all(db)
        # Level 1 has 17 practices; level 2/3 YAML are empty for now
        assert counts["practices"] == 17
        assert db.query(CMMCPractice).count() == 17

    def test_seed_is_idempotent(self, db):
        seed_all(db)
        seed_all(db)  # run again
        assert db.query(CMMCDomain).count() == 14
        assert db.query(CMMCPractice).count() == 17

    def test_seed_level_data(self, db):
        seed_all(db)
        level1 = db.query(CMMCLevel).filter_by(level=1).first()
        assert level1 is not None
        assert level1.name == "Foundational"
        assert level1.assessment_type == "self"

    def test_seed_practice_fk_valid(self, db):
        seed_all(db)
        practice = db.query(CMMCPractice).filter_by(practice_id="AC.L1-3.1.1").first()
        assert practice is not None
        assert practice.domain_ref == "AC"
        assert practice.domain.name == "Access Control"
