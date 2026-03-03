"""Model instantiation, FK relationships, and BaseModel behavior tests."""

import json
from datetime import date

from cmmc.models import (
    Assessment,
    AssessmentPractice,
    AuditLog,
    CMMCDomain,
    CMMCLevel,
    CMMCPractice,
    DataPactPracticeMapping,
    DataPactSyncLog,
    Evidence,
    Finding,
    Organization,
    POAM,
    POAMItem,
    Role,
    User,
    UserRole,
)


# ── BaseModel behavior ──────────────────────────────────────────────────────


class TestBaseModelBehavior:
    def test_auto_generates_id(self, db):
        org = Organization(name="Test Org")
        db.add(org)
        db.commit()
        assert org.id is not None
        assert len(org.id) == 16

    def test_sets_timestamps(self, db):
        org = Organization(name="Test Org")
        db.add(org)
        db.commit()
        assert org.created_at is not None
        assert org.updated_at is not None

    def test_creator_defaults_to_system(self, db):
        org = Organization(name="Test Org")
        db.add(org)
        db.commit()
        assert org.creator_id == "system"

    def test_row_version_starts_at_1(self, db):
        org = Organization(name="Test Org")
        db.add(org)
        db.commit()
        assert org.row_version == 1

    def test_row_version_increments_on_update(self, db):
        org = Organization(name="Test Org")
        db.add(org)
        db.commit()
        org.name = "Updated Org"
        db.commit()
        assert org.row_version == 2


# ── Reference data models ───────────────────────────────────────────────────


class TestCMMCDomain:
    def test_create_domain(self, db):
        d = CMMCDomain(domain_id="AC", name="Access Control", description="Limit access.")
        db.add(d)
        db.commit()
        assert d.id is not None
        assert d.domain_id == "AC"

    def test_domain_id_unique(self, db):
        db.add(CMMCDomain(domain_id="AC", name="Access Control"))
        db.commit()
        import pytest
        from sqlalchemy.exc import IntegrityError

        db.add(CMMCDomain(domain_id="AC", name="Duplicate"))
        with pytest.raises(IntegrityError):
            db.commit()


class TestCMMCLevel:
    def test_create_level(self, db):
        lvl = CMMCLevel(level=1, name="Foundational", assessment_type="self")
        db.add(lvl)
        db.commit()
        assert lvl.level == 1


class TestCMMCPractice:
    def test_create_practice_with_domain_fk(self, db):
        domain = CMMCDomain(domain_id="AC", name="Access Control")
        db.add(domain)
        db.commit()

        p = CMMCPractice(
            practice_id="AC.L1-3.1.1",
            domain_ref="AC",
            level=1,
            title="Authorized Access",
            nist_refs=json.dumps(["3.1.1"]),
        )
        db.add(p)
        db.commit()
        assert p.practice_id == "AC.L1-3.1.1"

    def test_practice_domain_relationship(self, db):
        domain = CMMCDomain(domain_id="SC", name="System and Comms")
        db.add(domain)
        db.commit()

        p = CMMCPractice(
            practice_id="SC.L1-3.13.1", domain_ref="SC", level=1, title="Boundary"
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        assert p.domain.name == "System and Comms"


# ── Organization & User models ──────────────────────────────────────────────


class TestOrganization:
    def test_create_organization(self, db):
        org = Organization(name="ACME Corp", cage_code="1ABC2", target_level=2)
        db.add(org)
        db.commit()
        assert org.name == "ACME Corp"


class TestUser:
    def test_create_user_with_org(self, db):
        org = Organization(name="ACME Corp")
        db.add(org)
        db.commit()

        user = User(
            username="jdoe",
            email="jdoe@acme.com",
            password_hash="$2b$fakehash",
            org_id=org.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.organization.name == "ACME Corp"
        assert user.is_active is True

    def test_username_unique(self, db):
        org = Organization(name="Org")
        db.add(org)
        db.commit()

        db.add(User(username="jdoe", email="a@b.com", password_hash="h", org_id=org.id))
        db.commit()

        import pytest
        from sqlalchemy.exc import IntegrityError

        db.add(User(username="jdoe", email="c@d.com", password_hash="h", org_id=org.id))
        with pytest.raises(IntegrityError):
            db.commit()


class TestRoleAndUserRole:
    def test_user_role_junction(self, db):
        org = Organization(name="Org")
        db.add(org)
        db.commit()

        role = Role(name="assessor")
        db.add(role)
        db.commit()

        user = User(username="u1", email="u1@x.com", password_hash="h", org_id=org.id)
        db.add(user)
        db.commit()

        ur = UserRole(user_id=user.id, role_id=role.id)
        db.add(ur)
        db.commit()

        db.refresh(user)
        assert len(user.roles) == 1
        assert user.roles[0].name == "assessor"


# ── Assessment models ────────────────────────────────────────────────────────


class TestAssessment:
    def test_create_assessment(self, db):
        org = Organization(name="Org")
        db.add(org)
        db.commit()

        a = Assessment(
            org_id=org.id,
            title="Annual Assessment",
            target_level=2,
            assessment_type="self",
        )
        db.add(a)
        db.commit()
        assert a.status == "draft"
        assert a.sprs_score is None


class TestAssessmentPractice:
    def test_create_assessment_practice(self, db):
        org = Organization(name="Org")
        db.add(org)
        db.commit()

        domain = CMMCDomain(domain_id="AC", name="Access Control")
        db.add(domain)
        db.commit()

        practice = CMMCPractice(
            practice_id="AC.L1-3.1.1", domain_ref="AC", level=1, title="Auth"
        )
        db.add(practice)
        db.commit()

        assessment = Assessment(
            org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        db.add(assessment)
        db.commit()

        ap = AssessmentPractice(
            assessment_id=assessment.id,
            practice_id="AC.L1-3.1.1",
        )
        db.add(ap)
        db.commit()
        assert ap.status == "not_evaluated"


# ── Evidence ─────────────────────────────────────────────────────────────────


class TestEvidence:
    def test_create_evidence(self, db):
        org = Organization(name="Org")
        domain = CMMCDomain(domain_id="AC", name="AC")
        db.add_all([org, domain])
        db.commit()

        practice = CMMCPractice(
            practice_id="AC.L1-3.1.1", domain_ref="AC", level=1, title="Auth"
        )
        db.add(practice)
        db.commit()

        assessment = Assessment(
            org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        db.add(assessment)
        db.commit()

        ap = AssessmentPractice(
            assessment_id=assessment.id, practice_id="AC.L1-3.1.1"
        )
        db.add(ap)
        db.commit()

        ev = Evidence(
            assessment_practice_id=ap.id,
            title="Screenshot of ACL config",
        )
        db.add(ev)
        db.commit()
        assert ev.review_status == "pending"


# ── Finding ──────────────────────────────────────────────────────────────────


class TestFinding:
    def test_create_finding(self, db):
        org = Organization(name="Org")
        db.add(org)
        db.commit()

        a = Assessment(
            org_id=org.id, title="Test", target_level=1, assessment_type="self"
        )
        db.add(a)
        db.commit()

        f = Finding(
            assessment_id=a.id,
            finding_type="deficiency",
            severity="high",
            title="Missing MFA",
        )
        db.add(f)
        db.commit()
        assert f.status == "open"


# ── POA&M models ─────────────────────────────────────────────────────────────


class TestPOAM:
    def test_create_poam_with_item(self, db):
        org = Organization(name="Org")
        db.add(org)
        db.commit()

        poam = POAM(org_id=org.id, title="Remediation Plan")
        db.add(poam)
        db.commit()
        assert poam.status == "draft"

        item = POAMItem(
            poam_id=poam.id,
            milestone="Deploy MFA",
            scheduled_completion=date(2026, 6, 30),
        )
        db.add(item)
        db.commit()
        assert item.risk_accepted is False

        db.refresh(poam)
        assert len(poam.items) == 1


# ── DataPact models ──────────────────────────────────────────────────────────


class TestDataPactModels:
    def test_create_practice_mapping(self, db):
        org = Organization(name="Org")
        domain = CMMCDomain(domain_id="AC", name="AC")
        db.add_all([org, domain])
        db.commit()

        practice = CMMCPractice(
            practice_id="AC.L1-3.1.1", domain_ref="AC", level=1, title="Auth"
        )
        db.add(practice)
        db.commit()

        mapping = DataPactPracticeMapping(
            org_id=org.id,
            practice_id="AC.L1-3.1.1",
            datapact_contract_id="contract-abc",
        )
        db.add(mapping)
        db.commit()
        assert mapping.datapact_contract_id == "contract-abc"

    def test_create_sync_log(self, db):
        org = Organization(name="Org")
        db.add(org)
        db.commit()

        log = DataPactSyncLog(
            org_id=org.id,
            status="success",
            request_payload=json.dumps({"action": "sync"}),
        )
        db.add(log)
        db.commit()
        assert log.status == "success"


# ── Audit log ────────────────────────────────────────────────────────────────


class TestAuditLog:
    def test_create_audit_log(self, db):
        log = AuditLog(
            action="assessment.create",
            resource_type="assessment",
            resource_id="abc123",
            ip_address="127.0.0.1",
        )
        db.add(log)
        db.commit()
        assert log.action == "assessment.create"


# ── Table count verification ─────────────────────────────────────────────────


class TestAllTablesPresent:
    def test_16_tables_registered(self):
        from cmmc.models.base import Base

        table_names = set(Base.metadata.tables.keys())
        expected = {
            "cmmc_domains",
            "cmmc_levels",
            "cmmc_practices",
            "organizations",
            "users",
            "roles",
            "user_roles",
            "assessments",
            "assessment_practices",
            "evidence",
            "findings",
            "poams",
            "poam_items",
            "datapact_practice_mappings",
            "datapact_sync_logs",
            "audit_log",
        }
        assert expected.issubset(table_names), f"Missing: {expected - table_names}"
