"""Full end-to-end smoke test — every API endpoint exercised.

Covers the entire CMMC application surface:
  Auth, Organizations, Users, CMMC Library, Assessments, Evidence,
  Findings, POA&Ms, Dashboard, Reports, DataPact, Audit, Health,
  Error handling (404, 401, 403, 409, 422), Status transitions,
  Org isolation, Seed data.
"""

import io
from unittest.mock import AsyncMock, patch

from sqlalchemy.orm import Session

from cmmc.models.cmmc_ref import CMMCDomain, CMMCLevel, CMMCPractice
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _uid() -> str:
    """Return a unique suffix to avoid username/email collisions across tests."""
    global _counter
    _counter += 1
    return f"{_counter}"


def _seed_roles(db: Session) -> None:
    for name in ("system_admin", "org_admin", "compliance_officer", "assessor", "c3pao_lead", "viewer"):
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name))
    db.commit()


def _seed_cmmc_data(db: Session) -> None:
    """Seed 2 domains, 2 levels, 5 practices (3 L1 + 1 L2 + 1 IA L1)."""
    if not db.query(CMMCDomain).filter_by(domain_id="AC").first():
        db.add(CMMCDomain(domain_id="AC", name="Access Control", description="AC"))
    if not db.query(CMMCDomain).filter_by(domain_id="IA").first():
        db.add(CMMCDomain(domain_id="IA", name="Identification and Authentication", description="IA"))
    if not db.query(CMMCLevel).filter_by(level=1).first():
        db.add(CMMCLevel(level=1, name="Foundational", assessment_type="self"))
    if not db.query(CMMCLevel).filter_by(level=2).first():
        db.add(CMMCLevel(level=2, name="Advanced", assessment_type="third_party"))
    db.flush()

    for i in range(1, 4):
        pid = f"AC.L1-b.1.{i:03d}"
        if not db.query(CMMCPractice).filter_by(practice_id=pid).first():
            db.add(CMMCPractice(practice_id=pid, domain_ref="AC", title=f"AC L1 practice {i}", level=1))
    if not db.query(CMMCPractice).filter_by(practice_id="AC.L2-b.1.001").first():
        db.add(CMMCPractice(practice_id="AC.L2-b.1.001", domain_ref="AC", title="AC L2 practice 1", level=2))
    if not db.query(CMMCPractice).filter_by(practice_id="IA.L1-b.1.001").first():
        db.add(CMMCPractice(practice_id="IA.L1-b.1.001", domain_ref="IA", title="IA L1 practice 1", level=1))
    db.commit()


def _make_user(
    db: Session, role_names: list[str], org_id: str | None = None,
) -> tuple[User, str]:
    n = _uid()
    user = User(
        username=f"user_{n}", email=f"user_{n}@test.com",
        password_hash=hash_password("password123"), org_id=org_id,
    )
    db.add(user)
    db.flush()
    for rname in role_names:
        role = db.query(Role).filter(Role.name == rname).first()
        if not role:
            role = Role(name=rname)
            db.add(role)
            db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id, role_names)


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_org(client, db, org_name="TestOrg"):
    """Create roles, admin user, and org. Returns (admin, token, org_data)."""
    _seed_roles(db)
    admin, token = _make_user(db, ["system_admin"])
    org = client.post("/api/organizations", json={"name": org_name}, headers=_h(token)).json()
    admin.org_id = org["id"]
    db.commit()
    return admin, token, org


def _complete_assessment(client, token, org_id, title="Test Assessment"):
    """Create, start, evaluate all met, submit, complete. Returns assessment_id."""
    assessment = client.post("/api/assessments", json={
        "org_id": org_id, "title": title, "target_level": 1, "assessment_type": "self",
    }, headers=_h(token)).json()
    aid = assessment["id"]
    client.post(f"/api/assessments/{aid}/start", headers=_h(token))
    practices = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()
    for p in practices:
        client.patch(f"/api/assessments/{aid}/practices/{p['practice_id']}",
            json={"status": "met", "score": 1.0}, headers=_h(token))
    client.post(f"/api/assessments/{aid}/submit", headers=_h(token))
    client.post(f"/api/assessments/{aid}/complete", headers=_h(token))
    return aid


# ===========================================================================
# Smoke Test
# ===========================================================================


class TestE2ESmoke:

    # ------------------------------------------------------------------
    # 1. Health
    # ------------------------------------------------------------------

    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    # ------------------------------------------------------------------
    # 2. Auth — register, login, refresh, me, update profile
    # ------------------------------------------------------------------

    def test_auth_register_login_refresh_me(self, client, db):
        _seed_roles(db)
        n = _uid()

        # Register
        resp = client.post("/api/auth/register", json={
            "username": f"smoke_{n}", "email": f"smoke_{n}@test.com", "password": "securepass1",
        })
        assert resp.status_code == 201
        assert resp.json()["username"] == f"smoke_{n}"

        # Login
        resp = client.post("/api/auth/login", json={"username": f"smoke_{n}", "password": "securepass1"})
        assert resp.status_code == 200
        tokens = resp.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        h = _h(tokens["access_token"])

        # GET /me
        resp = client.get("/api/auth/me", headers=h)
        assert resp.status_code == 200
        assert resp.json()["username"] == f"smoke_{n}"

        # PATCH /me
        resp = client.patch("/api/auth/me", json={"email": f"updated_{n}@test.com"}, headers=h)
        assert resp.status_code == 200
        assert resp.json()["email"] == f"updated_{n}@test.com"

        # Refresh token
        resp = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_auth_bad_login(self, client, db):
        _seed_roles(db)
        resp = client.post("/api/auth/login", json={"username": "nonexistent", "password": "wrong"})
        assert resp.status_code == 401

    def test_auth_duplicate_register(self, client, db):
        _seed_roles(db)
        n = _uid()
        client.post("/api/auth/register", json={"username": f"dup_{n}", "email": f"dup_{n}@t.com", "password": "password123"})
        resp = client.post("/api/auth/register", json={"username": f"dup_{n}", "email": f"dup2_{n}@t.com", "password": "password123"})
        assert resp.status_code == 409

    # ------------------------------------------------------------------
    # 3. Organizations — CRUD + datapact_tenant_id
    # ------------------------------------------------------------------

    def test_org_crud(self, client, db):
        _, token, _ = _setup_org(client, db, f"OrgCrud_{_uid()}")

        # Create
        resp = client.post("/api/organizations", json={
            "name": f"SmokeOrg_{_uid()}", "cage_code": "S1234", "target_level": 2,
        }, headers=_h(token))
        assert resp.status_code == 201
        org = resp.json()
        assert org["cage_code"] == "S1234"
        assert org["datapact_tenant_id"] is None
        oid = org["id"]

        # List
        resp = client.get("/api/organizations", headers=_h(token))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

        # Get
        resp = client.get(f"/api/organizations/{oid}", headers=_h(token))
        assert resp.status_code == 200

        # Update
        resp = client.patch(f"/api/organizations/{oid}", json={"name": f"Updated_{_uid()}"}, headers=_h(token))
        assert resp.status_code == 200

        # Delete
        resp = client.delete(f"/api/organizations/{oid}", headers=_h(token))
        assert resp.status_code == 204

        # Verify deleted
        resp = client.get(f"/api/organizations/{oid}", headers=_h(token))
        assert resp.status_code == 404

    def test_org_duplicate_name(self, client, db):
        _, token, org = _setup_org(client, db, f"DupOrg_{_uid()}")
        resp = client.post("/api/organizations", json={"name": org["name"]}, headers=_h(token))
        assert resp.status_code == 409

    def test_org_forbidden_non_admin(self, client, db):
        _seed_roles(db)
        _, viewer_token = _make_user(db, ["viewer"])
        resp = client.post("/api/organizations", json={"name": "Nope"}, headers=_h(viewer_token))
        assert resp.status_code == 403

    # ------------------------------------------------------------------
    # 4. Users — list, get, update, deactivate
    # ------------------------------------------------------------------

    def test_user_management(self, client, db):
        _, admin_token, org = _setup_org(client, db, f"UserOrg_{_uid()}")
        n = _uid()
        reg_resp = client.post("/api/auth/register", json={
            "username": f"managed_{n}", "email": f"managed_{n}@t.com", "password": "password123",
        })
        assert reg_resp.status_code == 201
        managed_id = reg_resp.json()["id"]

        # List
        resp = client.get("/api/users", headers=_h(admin_token))
        assert resp.status_code == 200

        # Get
        assert client.get(f"/api/users/{managed_id}", headers=_h(admin_token)).status_code == 200

        # Update
        resp = client.patch(f"/api/users/{managed_id}", json={
            "org_id": org["id"], "roles": ["compliance_officer"],
        }, headers=_h(admin_token))
        assert resp.status_code == 200
        assert resp.json()["org_id"] == org["id"]

        # Deactivate (soft delete — returns updated user or 204)
        resp = client.delete(f"/api/users/{managed_id}", headers=_h(admin_token))
        assert resp.status_code in (200, 204)

    # ------------------------------------------------------------------
    # 5. CMMC Library — domains, levels, practices
    # ------------------------------------------------------------------

    def test_cmmc_library(self, client, db):
        _seed_roles(db)
        _seed_cmmc_data(db)
        _, token = _make_user(db, ["viewer"])

        assert len(client.get("/api/cmmc/domains", headers=_h(token)).json()) == 2
        assert len(client.get("/api/cmmc/levels", headers=_h(token)).json()) == 2
        assert len(client.get("/api/cmmc/practices", headers=_h(token)).json()) == 5
        assert len(client.get("/api/cmmc/practices?level=1", headers=_h(token)).json()) == 4
        assert len(client.get("/api/cmmc/practices?domain=IA", headers=_h(token)).json()) == 1

        resp = client.get("/api/cmmc/practices/AC.L1-b.1.001", headers=_h(token))
        assert resp.status_code == 200
        assert client.get("/api/cmmc/practices/NONEXISTENT", headers=_h(token)).status_code == 404

    # ------------------------------------------------------------------
    # 6. Assessment lifecycle
    # ------------------------------------------------------------------

    def test_assessment_full_lifecycle(self, client, db):
        _seed_cmmc_data(db)
        admin, token, org = _setup_org(client, db, f"AssessOrg_{_uid()}")

        # Create
        resp = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Smoke", "target_level": 1, "assessment_type": "self",
        }, headers=_h(token))
        assert resp.status_code == 201
        aid = resp.json()["id"]
        assert resp.json()["status"] == "draft"

        # List & Get
        assert client.get("/api/assessments", headers=_h(token)).json()["total"] >= 1
        assert client.get(f"/api/assessments/{aid}", headers=_h(token)).status_code == 200

        # Update
        resp = client.patch(f"/api/assessments/{aid}", json={"title": "Updated"}, headers=_h(token))
        assert resp.json()["title"] == "Updated"

        # Start
        resp = client.post(f"/api/assessments/{aid}/start", headers=_h(token))
        assert resp.json()["status"] == "in_progress"

        # List & filter practices
        practices = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()
        assert len(practices) == 4

        # Get single practice
        pid = practices[0]["practice_id"]
        resp = client.get(f"/api/assessments/{aid}/practices/{pid}", headers=_h(token))
        assert resp.json()["status"] == "not_evaluated"

        # Evaluate
        for i, p in enumerate(practices):
            status = "met" if i < 3 else "not_met"
            resp = client.patch(f"/api/assessments/{aid}/practices/{p['practice_id']}",
                json={"status": status, "score": 1.0 if status == "met" else 0.0},
                headers=_h(token))
            assert resp.status_code == 200

        # Filter by status
        assert len(client.get(f"/api/assessments/{aid}/practices?status=met", headers=_h(token)).json()) == 3
        assert len(client.get(f"/api/assessments/{aid}/practices?domain=IA", headers=_h(token)).json()) == 1

        # Submit & Complete
        assert client.post(f"/api/assessments/{aid}/submit", headers=_h(token)).json()["status"] == "under_review"
        assert client.post(f"/api/assessments/{aid}/complete", headers=_h(token)).json()["status"] == "completed"

        # Cannot update completed
        assert client.patch(f"/api/assessments/{aid}", json={"title": "No"}, headers=_h(token)).status_code == 409

    # ------------------------------------------------------------------
    # 7. Evidence
    # ------------------------------------------------------------------

    def test_evidence_flow(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"EvidOrg_{_uid()}")

        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Evid", "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]
        client.post(f"/api/assessments/{aid}/start", headers=_h(token))
        practices = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()
        ap_id = practices[0]["id"]

        # Upload with file
        resp = client.post("/api/evidence",
            data={"assessment_practice_id": ap_id, "title": "Policy"},
            files={"file": ("policy.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
            headers=_h(token))
        assert resp.status_code == 201
        eid = resp.json()["id"]
        assert resp.json()["file_name"] == "policy.pdf"

        # Upload without file
        resp = client.post("/api/evidence",
            data={"assessment_practice_id": ap_id, "title": "URL Ref"}, headers=_h(token))
        assert resp.status_code == 201
        eid2 = resp.json()["id"]

        # List
        assert client.get(f"/api/evidence?assessment_practice_id={ap_id}", headers=_h(token)).json()["total"] == 2
        assert client.get(f"/api/evidence?assessment_id={aid}", headers=_h(token)).json()["total"] == 2

        # Get
        assert client.get(f"/api/evidence/{eid}", headers=_h(token)).status_code == 200

        # Review
        resp = client.post(f"/api/evidence/{eid}/review", json={"review_status": "accepted"}, headers=_h(token))
        assert resp.json()["review_status"] == "accepted"

        # Delete pending OK
        assert client.delete(f"/api/evidence/{eid2}", headers=_h(token)).status_code == 204
        # Delete reviewed fails
        assert client.delete(f"/api/evidence/{eid}", headers=_h(token)).status_code == 409

    # ------------------------------------------------------------------
    # 8. Findings
    # ------------------------------------------------------------------

    def test_findings_flow(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"FindOrg_{_uid()}")

        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Findings", "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]

        # Create
        f1 = client.post("/api/findings", json={
            "assessment_id": aid, "practice_id": "AC.L1-b.1.001",
            "finding_type": "deficiency", "severity": "high", "title": "F1",
        }, headers=_h(token)).json()
        assert f1["status"] == "open"
        f2 = client.post("/api/findings", json={
            "assessment_id": aid, "finding_type": "observation", "severity": "low", "title": "F2",
        }, headers=_h(token)).json()

        # List & filter
        assert client.get(f"/api/findings?assessment_id={aid}", headers=_h(token)).json()["total"] == 2
        assert client.get("/api/findings?finding_type=deficiency", headers=_h(token)).json()["total"] >= 1
        assert client.get("/api/findings?severity=high", headers=_h(token)).json()["total"] >= 1

        # Get
        assert client.get(f"/api/findings/{f1['id']}", headers=_h(token)).status_code == 200

        # Update
        resp = client.patch(f"/api/findings/{f1['id']}", json={"status": "resolved"}, headers=_h(token))
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

        # Delete open
        assert client.delete(f"/api/findings/{f2['id']}", headers=_h(token)).status_code == 204

    # ------------------------------------------------------------------
    # 9. POA&M
    # ------------------------------------------------------------------

    def test_poam_full_flow(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"POAMOrg_{_uid()}")
        aid = _complete_assessment(client, token, org["id"], "POAM Test")

        # Create findings
        practices = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()
        client.post("/api/findings", json={
            "assessment_id": aid, "practice_id": practices[0]["practice_id"],
            "finding_type": "deficiency", "severity": "high", "title": "PF1",
        }, headers=_h(token))
        client.post("/api/findings", json={
            "assessment_id": aid, "practice_id": practices[1]["practice_id"],
            "finding_type": "deficiency", "severity": "medium", "title": "PF2",
        }, headers=_h(token))

        # Create POA&M
        poam = client.post("/api/poams", json={
            "org_id": org["id"], "assessment_id": aid, "title": "Remediation",
        }, headers=_h(token)).json()
        assert poam["status"] == "draft"
        pid = poam["id"]

        # List
        assert client.get("/api/poams", headers=_h(token)).json()["total"] >= 1

        # Generate items from findings
        items = client.post(f"/api/poams/generate/{aid}?poam_id={pid}", headers=_h(token)).json()
        assert len(items) >= 2

        # Add manual item
        resp = client.post(f"/api/poams/{pid}/items", json={
            "milestone": "Deploy MFA", "scheduled_completion": "2026-12-31",
        }, headers=_h(token))
        assert resp.status_code == 201
        item_id = resp.json()["id"]

        # Get detail
        detail = client.get(f"/api/poams/{pid}", headers=_h(token)).json()
        assert len(detail["items"]) >= 3

        # Update item
        assert client.patch(f"/api/poams/{pid}/items/{item_id}", json={"status": "in_progress"}, headers=_h(token)).json()["status"] == "in_progress"

        # Activate → complete
        assert client.post(f"/api/poams/{pid}/activate", headers=_h(token)).json()["status"] == "active"

        # Remove item
        assert client.delete(f"/api/poams/{pid}/items/{item_id}", headers=_h(token)).status_code == 204

        assert client.post(f"/api/poams/{pid}/complete", headers=_h(token)).json()["status"] == "completed"

        # Cannot update completed
        assert client.patch(f"/api/poams/{pid}", json={"title": "No"}, headers=_h(token)).status_code == 409

    # ------------------------------------------------------------------
    # 10. Dashboard
    # ------------------------------------------------------------------

    def test_dashboard_all_endpoints(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"DashOrg_{_uid()}")
        aid = _complete_assessment(client, token, org["id"], "Dashboard Test")

        client.post("/api/findings", json={
            "assessment_id": aid, "finding_type": "observation", "severity": "low", "title": "DF",
        }, headers=_h(token))

        assert client.get("/api/dashboard/summary", headers=_h(token)).status_code == 200
        assert client.get(f"/api/dashboard/summary?org_id={org['id']}", headers=_h(token)).status_code == 200

        domains = client.get(f"/api/dashboard/domain-compliance/{aid}", headers=_h(token)).json()
        assert len(domains) >= 1
        assert domains[0]["percentage"] == 100.0

        assert client.get(f"/api/dashboard/sprs-history/{org['id']}", headers=_h(token)).status_code == 200
        assert len(client.get(f"/api/dashboard/timeline/{org['id']}", headers=_h(token)).json()) >= 1
        assert client.get(f"/api/dashboard/findings-summary/{aid}", headers=_h(token)).json()["total"] == 1

    # ------------------------------------------------------------------
    # 11. Reports — CSV, PDF, SPRS
    # ------------------------------------------------------------------

    def test_reports(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"RepOrg_{_uid()}")
        aid = _complete_assessment(client, token, org["id"], "Report Test")

        # CSV
        resp = client.get(f"/api/reports/assessment/{aid}?format=csv", headers=_h(token))
        assert resp.status_code == 200
        assert b"Assessment Report" in resp.content
        assert b"Mapped Contracts" in resp.content

        # PDF
        resp = client.get(f"/api/reports/assessment/{aid}?format=pdf", headers=_h(token))
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

        # Default format
        assert client.get(f"/api/reports/assessment/{aid}", headers=_h(token)).status_code == 200

        # Invalid format
        resp = client.get(f"/api/reports/assessment/{aid}?format=xml", headers=_h(token))
        assert resp.status_code in (400, 422)  # FastAPI validates query params as 422

        # SPRS
        assert client.get(f"/api/reports/sprs/{org['id']}", headers=_h(token)).status_code == 200

    # ------------------------------------------------------------------
    # 12. DataPact — contracts, mappings, suggest, sync, logs
    # ------------------------------------------------------------------

    def test_datapact_contracts_proxy(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"DPOrg_{_uid()}")

        with patch("cmmc.routers.datapact._client_for_user") as mock_factory:
            mc = AsyncMock()
            mc.get_contracts.return_value = {"items": [{"id": "c1", "title": "Alpha"}], "total": 1}
            mock_factory.return_value = mc
            resp = client.get("/api/datapact/contracts", headers=_h(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_datapact_mappings_crud(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"MapOrg_{_uid()}")

        # Create
        resp = client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001", "datapact_contract_id": "c1",
            "datapact_contract_name": "Alpha",
        }, headers=_h(token))
        assert resp.status_code == 201
        mid = resp.json()["id"]

        # List
        assert client.get("/api/datapact/mappings", headers=_h(token)).json()["total"] == 1
        assert client.get("/api/datapact/mappings?practice_id=AC.L1-b.1.001", headers=_h(token)).json()["total"] == 1
        assert client.get("/api/datapact/mappings?practice_id=NONE", headers=_h(token)).json()["total"] == 0

        # Duplicate
        assert client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001", "datapact_contract_id": "c1",
        }, headers=_h(token)).status_code == 409

        # Delete
        assert client.delete(f"/api/datapact/mappings/{mid}", headers=_h(token)).status_code == 204
        assert client.delete("/api/datapact/mappings/nonexistent", headers=_h(token)).status_code == 404

    def test_datapact_suggest(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"SugOrg_{_uid()}")

        with patch("cmmc.routers.datapact._client_for_user") as mock_factory:
            mc = AsyncMock()
            mc.get_contracts.return_value = {"items": [
                {"id": "c1", "title": "Access Control", "description": "authentication"},
                {"id": "c2", "title": "Widget", "description": "manufacturing"},
            ], "total": 2}
            mock_factory.return_value = mc
            resp = client.post("/api/datapact/suggest", headers=_h(token))
        assert resp.status_code == 200
        cids = {s["contract_id"] for s in resp.json()}
        assert "c1" in cids
        assert "c2" not in cids

    def test_datapact_sync_and_logs(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"SyncOrg_{_uid()}")

        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Sync", "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]
        client.post(f"/api/assessments/{aid}/start", headers=_h(token))
        practices = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()

        client.post("/api/datapact/mappings", json={
            "practice_id": practices[0]["practice_id"], "datapact_contract_id": "c1",
        }, headers=_h(token))

        compliance = {"contract_id": "c1", "status": "compliant", "score": 95.0,
            "details": {"total_clauses": 10, "compliant": 9, "non_compliant": 1}}

        # Sync single
        with patch("cmmc.services.sync_service.DataPactClient") as MC:
            mi = AsyncMock()
            mi.get_contract_compliance.return_value = compliance
            MC.return_value = mi
            resp = client.post(f"/api/datapact/sync/{aid}/{practices[0]['practice_id']}", headers=_h(token))
        assert resp.json()["status"] == "success"

        # Sync full
        with patch("cmmc.services.sync_service.DataPactClient") as MC:
            mi = AsyncMock()
            mi.get_contract_compliance.return_value = compliance
            MC.return_value = mi
            resp = client.post(f"/api/datapact/sync/{aid}", headers=_h(token))
        assert len(resp.json()["results"]) >= 1

        # Logs
        assert client.get("/api/datapact/sync-logs", headers=_h(token)).json()["total"] >= 1
        assert client.get(f"/api/datapact/sync-logs?assessment_id={aid}", headers=_h(token)).json()["total"] >= 1

    # ------------------------------------------------------------------
    # 13. Audit log
    # ------------------------------------------------------------------

    def test_audit_log(self, client, db):
        _, token, _ = _setup_org(client, db, f"AuditOrg_{_uid()}")
        db.expire_all()

        resp = client.get("/api/audit-log", headers=_h(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

        log_id = data["items"][0]["id"]
        assert client.get(f"/api/audit-log/{log_id}", headers=_h(token)).status_code == 200
        assert client.get("/api/audit-log?action=create", headers=_h(token)).status_code == 200

        # Non-admin forbidden
        _, viewer_token = _make_user(db, ["viewer"])
        assert client.get("/api/audit-log", headers=_h(viewer_token)).status_code == 403

    # ------------------------------------------------------------------
    # 14. Error handling
    # ------------------------------------------------------------------

    def test_unauthenticated_requests(self, client):
        # Note: /api/cmmc/* endpoints are public (no auth required)
        for path in ["/api/organizations", "/api/assessments", "/api/users",
                     "/api/findings", "/api/poams",
                     "/api/dashboard/summary", "/api/datapact/contracts", "/api/audit-log"]:
            assert client.get(path).status_code == 401, f"{path} should require auth"

    def test_not_found_responses(self, client, db):
        _, token, _ = _setup_org(client, db, f"NF_{_uid()}")
        for path in ["/api/organizations/x", "/api/assessments/x", "/api/findings/x",
                     "/api/poams/x", "/api/evidence/x", "/api/audit-log/x"]:
            assert client.get(path, headers=_h(token)).status_code == 404, f"{path}"

    def test_validation_errors(self, client, db):
        _, token, _ = _setup_org(client, db, f"Val_{_uid()}")
        assert client.post("/api/organizations", json={}, headers=_h(token)).status_code == 422
        assert client.post("/api/organizations", json={"name": "X", "target_level": 5}, headers=_h(token)).status_code == 422
        assert client.post("/api/assessments", json={}, headers=_h(token)).status_code == 422

    # ------------------------------------------------------------------
    # 15. Status transitions
    # ------------------------------------------------------------------

    def test_invalid_status_transitions(self, client, db):
        _seed_cmmc_data(db)
        _, token, org = _setup_org(client, db, f"Trans_{_uid()}")

        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "T", "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]

        # Cannot submit/complete draft
        assert client.post(f"/api/assessments/{aid}/submit", headers=_h(token)).status_code == 409
        assert client.post(f"/api/assessments/{aid}/complete", headers=_h(token)).status_code == 409

        # Start, then cannot complete without submit
        client.post(f"/api/assessments/{aid}/start", headers=_h(token))
        assert client.post(f"/api/assessments/{aid}/complete", headers=_h(token)).status_code == 409

    # ------------------------------------------------------------------
    # 16. Org isolation
    # ------------------------------------------------------------------

    def test_org_isolation(self, client, db):
        _seed_cmmc_data(db)
        _, admin_token, org_a = _setup_org(client, db, f"IsoA_{_uid()}")
        org_b = client.post("/api/organizations", json={"name": f"IsoB_{_uid()}"}, headers=_h(admin_token)).json()

        _, user_a_token = _make_user(db, ["assessor"], org_id=org_a["id"])

        assessment_b = client.post("/api/assessments", json={
            "org_id": org_b["id"], "title": "OrgB", "target_level": 1, "assessment_type": "self",
        }, headers=_h(admin_token)).json()

        assert client.get(f"/api/assessments/{assessment_b['id']}", headers=_h(user_a_token)).status_code == 403
        assert client.get(f"/api/organizations/{org_b['id']}", headers=_h(user_a_token)).status_code == 403

    # ------------------------------------------------------------------
    # 17. Seed data
    # ------------------------------------------------------------------

    def test_seed_service(self, db):
        from cmmc.services.seed_service import seed_all
        counts = seed_all(db, seed_demo=True)
        assert counts["domains"] > 0
        assert counts["roles"] == 6
        assert counts["findings"] > 0
        assert counts["poams"] > 0
        counts2 = seed_all(db, seed_demo=True)
        assert counts2["domains"] == counts["domains"]
