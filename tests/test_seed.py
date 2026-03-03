"""Seed service tests."""

from cmmc.models import CMMCDomain, CMMCLevel, CMMCPractice
from cmmc.models.user import Role
from cmmc.services.seed_service import DEFAULT_ROLES, seed_all


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
        # L1=17 + L2=93 + L3=24 = 134 total practices
        assert counts["practices"] == 134
        assert db.query(CMMCPractice).count() == 134

    def test_seed_creates_roles(self, db):
        counts = seed_all(db)
        assert counts["roles"] == 6
        assert db.query(Role).count() == 6
        role_names = {r.name for r in db.query(Role).all()}
        assert role_names == set(DEFAULT_ROLES)

    def test_seed_is_idempotent(self, db):
        seed_all(db)
        seed_all(db)  # run again
        assert db.query(CMMCDomain).count() == 14
        assert db.query(CMMCPractice).count() == 134
        assert db.query(Role).count() == 6

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

    def test_seed_level2_practices(self, db):
        seed_all(db)
        l2_count = db.query(CMMCPractice).filter_by(level=2).count()
        assert l2_count == 93
        # Verify a specific L2 practice
        p = db.query(CMMCPractice).filter_by(practice_id="AC.L2-3.1.3").first()
        assert p is not None
        assert p.domain_ref == "AC"
        assert p.level == 2

    def test_seed_level3_practices(self, db):
        seed_all(db)
        l3_count = db.query(CMMCPractice).filter_by(level=3).count()
        assert l3_count == 24
        # Verify a specific L3 practice
        p = db.query(CMMCPractice).filter_by(practice_id="RA.L3-3.11.1e").first()
        assert p is not None
        assert p.domain_ref == "RA"
        assert p.level == 3

    def test_seed_practice_counts_by_level(self, db):
        seed_all(db)
        l1 = db.query(CMMCPractice).filter_by(level=1).count()
        l2 = db.query(CMMCPractice).filter_by(level=2).count()
        l3 = db.query(CMMCPractice).filter_by(level=3).count()
        assert l1 == 17
        assert l2 == 93
        assert l3 == 24
        assert l1 + l2 + l3 == 134
