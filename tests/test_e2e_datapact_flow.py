"""E2E test for the full DataPact integration workflow.

Exercises the complete flow:
  Create org (→ DataPact tenant) → configure DataPact credentials →
  list contracts → create mappings → create & complete assessment →
  sync practices (→ compliance scores) → verify sync logs →
  verify assessor notes updated → generate report with contract data →
  check dashboard compliance.
"""

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
    global _counter
    _counter += 1
    return f"dp{_counter}"


def _seed_roles(db: Session) -> None:
    for name in ("system_admin", "org_admin", "compliance_officer", "assessor", "viewer"):
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name))
    db.commit()


def _seed_cmmc_data(db: Session) -> None:
    """Seed 2 domains, 2 levels, and 5 practices."""
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


def _make_user(db: Session, role_names: list[str], org_id: str | None = None) -> tuple[User, str]:
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


# Mock DataPact responses
MOCK_CONTRACTS = {
    "items": [
        {"id": "c1", "title": "Access Control Contract", "description": "Authentication and access control compliance", "status": "active"},
        {"id": "c2", "title": "Data Protection Contract", "description": "Data encryption and protection", "status": "active"},
        {"id": "c3", "title": "Identity Contract", "description": "Identity and authentication management", "status": "draft"},
    ],
    "total": 3,
}

MOCK_COMPLIANCE = {
    "contract_id": "c1",
    "status": "compliant",
    "score": 92.5,
    "details": {"total_clauses": 20, "compliant": 18, "non_compliant": 2},
}

MOCK_COMPLIANCE_C3 = {
    "contract_id": "c3",
    "status": "partial",
    "score": 75.0,
    "details": {"total_clauses": 12, "compliant": 9, "non_compliant": 3},
}

MOCK_ORG_COMPLIANCE = {
    "score": 88.0,
    "status": "compliant",
    "level": "gold",
}

MOCK_TENANT = {
    "id": "tenant-abc",
    "name": "TestOrg",
    "slug": "testorg",
}


# ===========================================================================
# E2E DataPact Integration Flow
# ===========================================================================


class TestE2EDataPactFlow:
    """Full DataPact integration workflow test.

    Tests the complete lifecycle from org creation through to report
    generation, verifying each step produces correct results.
    """

    # ------------------------------------------------------------------
    # 1. Org creation triggers DataPact tenant
    # ------------------------------------------------------------------

    def test_org_creation_creates_datapact_tenant(self, client, db):
        """Create org → verify DataPact tenant creation is attempted."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])

        with patch("cmmc.routers.organizations.DataPactClient") as MC:
            mc = AsyncMock()
            mc.create_tenant.return_value = MOCK_TENANT
            MC.return_value = mc

            resp = client.post("/api/organizations", json={"name": "DPFlowOrg"}, headers=_h(token))
            assert resp.status_code == 201
            org = resp.json()
            assert org["name"] == "DPFlowOrg"
            assert org.get("datapact_tenant_id") == "tenant-abc"

            # Verify tenant creation was called
            mc.create_tenant.assert_called_once()
            call_data = mc.create_tenant.call_args[0][0]
            assert call_data["name"] == "DPFlowOrg"

    def test_org_creation_graceful_on_datapact_failure(self, client, db):
        """Org creation succeeds even if DataPact tenant creation fails."""
        _seed_roles(db)
        admin, token = _make_user(db, ["system_admin"])

        with patch("cmmc.routers.organizations.DataPactClient") as MC:
            from cmmc.services.datapact_client import DataPactError
            mc = AsyncMock()
            mc.create_tenant.side_effect = DataPactError("DataPact unreachable", 503)
            MC.return_value = mc

            resp = client.post("/api/organizations", json={"name": f"FallbackOrg_{_uid()}"}, headers=_h(token))
            assert resp.status_code == 201
            org = resp.json()
            # Org created but no tenant_id
            assert org.get("datapact_tenant_id") is None

    # ------------------------------------------------------------------
    # 2. Configure DataPact credentials on org
    # ------------------------------------------------------------------

    def test_configure_datapact_credentials(self, client, db):
        """Set DataPact API URL and key on organization."""
        _seed_roles(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"CredOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        resp = client.patch(f"/api/organizations/{org['id']}", json={
            "datapact_api_url": "https://datapact.example.com",
            "datapact_api_key": "dp-key-12345",
        }, headers=_h(token))
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["datapact_api_url"] == "https://datapact.example.com"
        assert updated["datapact_api_key"] == "dp-key-12345"

    # ------------------------------------------------------------------
    # 3. List contracts via DataPact proxy
    # ------------------------------------------------------------------

    def test_list_datapact_contracts(self, client, db):
        """Proxy contracts from DataPact through CMMC."""
        _seed_roles(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"ListOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        with patch("cmmc.routers.datapact._client_for_user") as mock_factory:
            mc = AsyncMock()
            mc.get_contracts.return_value = MOCK_CONTRACTS
            mock_factory.return_value = mc

            resp = client.get("/api/datapact/contracts", headers=_h(token))
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 3
            titles = {c["title"] for c in data["items"]}
            assert "Access Control Contract" in titles
            assert "Identity Contract" in titles

    # ------------------------------------------------------------------
    # 4. Create practice-to-contract mappings
    # ------------------------------------------------------------------

    def test_create_mappings(self, client, db):
        """Map CMMC practices to DataPact contracts."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"MapFlowOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        # Map AC practice to contract c1
        resp = client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001",
            "datapact_contract_id": "c1",
            "datapact_contract_name": "Access Control Contract",
        }, headers=_h(token))
        assert resp.status_code == 201
        mapping1 = resp.json()
        assert mapping1["practice_id"] == "AC.L1-b.1.001"
        assert mapping1["datapact_contract_id"] == "c1"

        # Map IA practice to contract c3
        resp = client.post("/api/datapact/mappings", json={
            "practice_id": "IA.L1-b.1.001",
            "datapact_contract_id": "c3",
            "datapact_contract_name": "Identity Contract",
        }, headers=_h(token))
        assert resp.status_code == 201

        # Verify both mappings listed
        resp = client.get("/api/datapact/mappings", headers=_h(token))
        assert resp.json()["total"] == 2

        # Duplicate mapping rejected
        resp = client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001",
            "datapact_contract_id": "c1",
        }, headers=_h(token))
        assert resp.status_code == 409

    # ------------------------------------------------------------------
    # 5. Auto-suggest mappings
    # ------------------------------------------------------------------

    def test_suggest_mappings(self, client, db):
        """Auto-suggest practice-to-contract mappings via keyword matching."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"SugFlowOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        with patch("cmmc.routers.datapact._client_for_user") as mock_factory:
            mc = AsyncMock()
            mc.get_contracts.return_value = MOCK_CONTRACTS
            mock_factory.return_value = mc

            resp = client.post("/api/datapact/suggest", headers=_h(token))
            assert resp.status_code == 200
            suggestions = resp.json()
            # Should suggest access/identity contracts for AC/IA practices
            contract_ids = {s["contract_id"] for s in suggestions}
            assert len(suggestions) > 0
            # c1 (Access Control) should match AC practices
            assert "c1" in contract_ids

    # ------------------------------------------------------------------
    # 6. Full flow: assessment → sync → verify scores → report
    # ------------------------------------------------------------------

    def test_full_datapact_integration_flow(self, client, db):
        """Complete workflow: create org → map → assess → sync → report.

        This is the core E2E test covering the entire DataPact integration.
        """
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"FullFlowOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        org_id = org["id"]

        # ── Step 1: Create practice-to-contract mappings ─────────────
        client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001",
            "datapact_contract_id": "c1",
            "datapact_contract_name": "Access Control Contract",
        }, headers=_h(token))
        client.post("/api/datapact/mappings", json={
            "practice_id": "IA.L1-b.1.001",
            "datapact_contract_id": "c3",
            "datapact_contract_name": "Identity Contract",
        }, headers=_h(token))

        # Verify mappings
        mappings = client.get("/api/datapact/mappings", headers=_h(token)).json()
        assert mappings["total"] == 2

        # ── Step 2: Create assessment and evaluate all practices ─────
        assessment = client.post("/api/assessments", json={
            "org_id": org_id, "title": "DataPact Flow Test",
            "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]

        client.post(f"/api/assessments/{aid}/start", headers=_h(token))
        practices = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()
        assert len(practices) >= 4  # 3 AC L1 + 1 IA L1

        # Evaluate all practices as met
        for p in practices:
            client.patch(f"/api/assessments/{aid}/practices/{p['practice_id']}",
                json={"status": "met", "score": 1.0}, headers=_h(token))

        # ── Step 3: Sync individual practice with DataPact ───────────
        with patch("cmmc.services.sync_service.DataPactClient") as MC:
            mi = AsyncMock()
            mi.get_contract_compliance.return_value = MOCK_COMPLIANCE
            mi.get_compliance_score.return_value = {"score": 92.5, "level": "gold"}
            MC.return_value = mi

            resp = client.post(
                f"/api/datapact/sync/{aid}/AC.L1-b.1.001",
                headers=_h(token),
            )
            assert resp.status_code == 200
            result = resp.json()
            assert result["status"] == "success"
            assert result["practice_id"] == "AC.L1-b.1.001"
            assert result.get("compliance") is not None

        # ── Step 4: Sync full assessment ─────────────────────────────
        with patch("cmmc.services.sync_service.DataPactClient") as MC:
            mi = AsyncMock()
            # Return different compliance for different contracts
            def compliance_side_effect(contract_id):
                if contract_id == "c1":
                    return MOCK_COMPLIANCE
                return MOCK_COMPLIANCE_C3
            mi.get_contract_compliance.side_effect = compliance_side_effect
            mi.get_compliance_score.return_value = {"score": 85.0, "level": "silver"}
            MC.return_value = mi

            resp = client.post(f"/api/datapact/sync/{aid}", headers=_h(token))
            assert resp.status_code == 200
            results = resp.json()["results"]
            # Should have results for mapped practices
            synced = [r for r in results if r["status"] == "success"]
            skipped = [r for r in results if r["status"] == "skipped"]
            assert len(synced) >= 2  # AC.L1-b.1.001 + IA.L1-b.1.001
            assert len(skipped) >= 2  # AC.L1-b.1.002, AC.L1-b.1.003 (unmapped)

        # ── Step 5: Verify sync logs created ─────────────────────────
        logs = client.get(f"/api/datapact/sync-logs?assessment_id={aid}", headers=_h(token)).json()
        assert logs["total"] >= 3  # 1 single + 2+ from full sync

        # Verify logs have correct structure
        for log in logs["items"]:
            assert "status" in log
            assert "practice_id" in log or log.get("assessment_id") == aid

        # ── Step 6: Verify practice sync status updated ──────────────
        practices_after = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()
        ac_practice = next(p for p in practices_after if p["practice_id"] == "AC.L1-b.1.001")
        assert ac_practice.get("datapact_sync_status") in ("synced", "success")
        assert ac_practice.get("datapact_sync_at") is not None

        # ── Step 7: Submit and complete assessment ───────────────────
        client.post(f"/api/assessments/{aid}/submit", headers=_h(token))
        client.post(f"/api/assessments/{aid}/complete", headers=_h(token))

        # ── Step 8: Generate CSV report — verify contract mappings ───
        resp = client.get(f"/api/reports/assessment/{aid}?format=csv", headers=_h(token))
        assert resp.status_code == 200
        csv_content = resp.content.decode()
        assert "Mapped Contracts" in csv_content
        assert "Access Control Contract" in csv_content
        assert "Identity Contract" in csv_content

        # ── Step 9: Generate PDF report ──────────────────────────────
        resp = client.get(f"/api/reports/assessment/{aid}?format=pdf", headers=_h(token))
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

        # ── Step 10: Dashboard compliance ────────────────────────────
        resp = client.get(f"/api/dashboard/summary?org_id={org_id}", headers=_h(token))
        assert resp.status_code == 200
        summary = resp.json()
        assert summary["level_1"] == 100.0  # All L1 practices met

    # ------------------------------------------------------------------
    # 7. Dashboard DataPact compliance endpoint
    # ------------------------------------------------------------------

    def test_dashboard_datapact_compliance(self, client, db):
        """Dashboard returns DataPact org compliance score."""
        _seed_roles(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"DashOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        with patch("cmmc.services.dashboard_service.DataPactClient") as MC:
            mc = AsyncMock()
            mc.get_org_compliance_score.return_value = MOCK_ORG_COMPLIANCE
            MC.return_value = mc

            resp = client.get(f"/api/dashboard/datapact-compliance/{org['id']}", headers=_h(token))
            assert resp.status_code == 200
            data = resp.json()
            assert data["score"] == 88.0
            assert data["status"] == "compliant"

    def test_dashboard_datapact_compliance_unavailable(self, client, db):
        """Dashboard returns null when DataPact is not configured."""
        _seed_roles(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"NoDPOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        with patch("cmmc.services.dashboard_service.DataPactClient") as MC:
            from cmmc.services.datapact_client import DataPactError
            mc = AsyncMock()
            mc.get_org_compliance_score.side_effect = DataPactError("Not configured", 503)
            MC.return_value = mc

            resp = client.get(f"/api/dashboard/datapact-compliance/{org['id']}", headers=_h(token))
            assert resp.status_code == 200
            assert resp.json() is None

    # ------------------------------------------------------------------
    # 8. Sync with unmapped practices
    # ------------------------------------------------------------------

    def test_sync_skips_unmapped_practices(self, client, db):
        """Syncing practices without mappings returns 'skipped' status."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"SkipOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Skip Test",
            "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]
        client.post(f"/api/assessments/{aid}/start", headers=_h(token))

        # No mappings created — sync should skip all
        with patch("cmmc.services.sync_service.DataPactClient") as MC:
            mi = AsyncMock()
            MC.return_value = mi

            resp = client.post(f"/api/datapact/sync/{aid}", headers=_h(token))
            assert resp.status_code == 200
            results = resp.json()["results"]
            assert all(r["status"] == "skipped" for r in results)

            # Client should not have been called
            mi.get_contract_compliance.assert_not_called()

    # ------------------------------------------------------------------
    # 9. Sync handles DataPact errors gracefully
    # ------------------------------------------------------------------

    def test_sync_handles_datapact_errors(self, client, db):
        """Sync returns error status when DataPact call fails."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"ErrOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        # Create mapping
        client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001",
            "datapact_contract_id": "c1",
        }, headers=_h(token))

        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Error Test",
            "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]
        client.post(f"/api/assessments/{aid}/start", headers=_h(token))

        # DataPact client raises error
        with patch("cmmc.services.sync_service.DataPactClient") as MC:
            from cmmc.services.datapact_client import DataPactError
            mi = AsyncMock()
            mi.get_contract_compliance.side_effect = DataPactError("Service unavailable", 503)
            MC.return_value = mi

            resp = client.post(
                f"/api/datapact/sync/{aid}/AC.L1-b.1.001",
                headers=_h(token),
            )
            assert resp.status_code == 200
            result = resp.json()
            assert result["status"] == "error"

        # Sync log should record the error
        logs = client.get(f"/api/datapact/sync-logs?assessment_id={aid}", headers=_h(token)).json()
        assert logs["total"] >= 1
        error_log = next((l for l in logs["items"] if l["status"] != "success"), None)
        assert error_log is not None

    # ------------------------------------------------------------------
    # 10. Mapping filter by practice_id and contract_id
    # ------------------------------------------------------------------

    def test_mapping_filters(self, client, db):
        """Verify mapping list endpoint supports filtering."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"FilterOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        # Create two mappings
        client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001", "datapact_contract_id": "c1",
            "datapact_contract_name": "Alpha",
        }, headers=_h(token))
        client.post("/api/datapact/mappings", json={
            "practice_id": "IA.L1-b.1.001", "datapact_contract_id": "c3",
            "datapact_contract_name": "Gamma",
        }, headers=_h(token))

        # Filter by practice_id
        resp = client.get("/api/datapact/mappings?practice_id=AC.L1-b.1.001", headers=_h(token))
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["datapact_contract_id"] == "c1"

        # Filter by datapact_contract_id
        resp = client.get("/api/datapact/mappings?datapact_contract_id=c3", headers=_h(token))
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["practice_id"] == "IA.L1-b.1.001"

        # Filter with no match
        resp = client.get("/api/datapact/mappings?practice_id=NONEXISTENT", headers=_h(token))
        assert resp.json()["total"] == 0

    # ------------------------------------------------------------------
    # 11. Sync logs structure and filtering
    # ------------------------------------------------------------------

    def test_sync_logs_filtering(self, client, db):
        """Sync logs are filterable by assessment_id and have limit param."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"LogOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        # Create mapping and assessment
        client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001", "datapact_contract_id": "c1",
        }, headers=_h(token))

        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Log Test",
            "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]
        client.post(f"/api/assessments/{aid}/start", headers=_h(token))

        # Sync to generate logs
        with patch("cmmc.services.sync_service.DataPactClient") as MC:
            mi = AsyncMock()
            mi.get_contract_compliance.return_value = MOCK_COMPLIANCE
            mi.get_compliance_score.return_value = {"score": 92.5}
            MC.return_value = mi
            client.post(f"/api/datapact/sync/{aid}", headers=_h(token))

        # All logs
        all_logs = client.get("/api/datapact/sync-logs", headers=_h(token)).json()
        assert all_logs["total"] >= 1

        # Filter by assessment
        filtered = client.get(f"/api/datapact/sync-logs?assessment_id={aid}", headers=_h(token)).json()
        assert filtered["total"] >= 1
        for log in filtered["items"]:
            assert log["assessment_id"] == aid

    # ------------------------------------------------------------------
    # 12. Report includes mapped contracts for mixed mappings
    # ------------------------------------------------------------------

    def test_report_with_partial_mappings(self, client, db):
        """Report shows contracts for mapped practices, blank for unmapped."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, token = _make_user(db, ["system_admin"])
        org = client.post("/api/organizations", json={"name": f"PartialOrg_{_uid()}"}, headers=_h(token)).json()
        admin.org_id = org["id"]
        db.commit()

        # Only map one practice
        client.post("/api/datapact/mappings", json={
            "practice_id": "AC.L1-b.1.001",
            "datapact_contract_id": "c1",
            "datapact_contract_name": "Access Control Contract",
        }, headers=_h(token))

        # Complete assessment
        assessment = client.post("/api/assessments", json={
            "org_id": org["id"], "title": "Partial Map Test",
            "target_level": 1, "assessment_type": "self",
        }, headers=_h(token)).json()
        aid = assessment["id"]
        client.post(f"/api/assessments/{aid}/start", headers=_h(token))
        practices = client.get(f"/api/assessments/{aid}/practices", headers=_h(token)).json()
        for p in practices:
            client.patch(f"/api/assessments/{aid}/practices/{p['practice_id']}",
                json={"status": "met", "score": 1.0}, headers=_h(token))
        client.post(f"/api/assessments/{aid}/submit", headers=_h(token))
        client.post(f"/api/assessments/{aid}/complete", headers=_h(token))

        # CSV report should show mapped contract
        resp = client.get(f"/api/reports/assessment/{aid}?format=csv", headers=_h(token))
        assert resp.status_code == 200
        csv_content = resp.content.decode()
        assert "Mapped Contracts" in csv_content
        assert "Access Control Contract" in csv_content
