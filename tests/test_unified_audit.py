"""Tests for unified audit log — merging CMMC and DataPact audit entries."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy.orm import Session

from cmmc.models.audit import AuditLog
from cmmc.models.organization import Organization
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _uid() -> str:
    global _counter
    _counter += 1
    return f"ua{_counter}"


def _seed_roles(db: Session) -> None:
    for name in ("system_admin", "org_admin", "viewer"):
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name))
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


def _make_org(db: Session, name: str | None = None, api_url: str | None = None) -> Organization:
    org = Organization(
        name=name or f"AuditOrg_{_uid()}",
        datapact_api_url=api_url,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _seed_audit_logs(db: Session, count: int = 3) -> list[AuditLog]:
    logs = []
    for i in range(count):
        log = AuditLog(
            user_id=None,
            action=["create", "update", "delete"][i % 3],
            resource_type=["assessments", "organizations", "poams"][i % 3],
            resource_id=f"r{i}",
            details={"method": "POST", "path": f"/api/test/{i}", "status_code": 200},
            ip_address="127.0.0.1",
        )
        db.add(log)
        logs.append(log)
    db.commit()
    for log in logs:
        db.refresh(log)
    return logs


MOCK_DP_AUDIT = {
    "items": [
        {
            "id": "dp-log-1",
            "action": "create",
            "resource_type": "contract",
            "resource_id": "c1",
            "user_id": "dp-user-1",
            "details": {"description": "Contract created"},
            "created_at": "2026-03-15T10:00:00Z",
        },
        {
            "id": "dp-log-2",
            "action": "update",
            "resource_type": "tenant",
            "resource_id": "t1",
            "user_id": "dp-user-2",
            "details": {"description": "Tenant updated"},
            "created_at": "2026-03-16T14:30:00Z",
        },
    ],
    "total": 2,
}


# ===========================================================================
# Tests
# ===========================================================================


class TestUnifiedAuditEndpoint:
    """Tests for GET /api/audit-log/unified."""

    def test_returns_cmmc_logs_only_when_no_datapact(self, client, db):
        """When org has no DataPact config, returns only CMMC logs."""
        _seed_roles(db)
        org = _make_org(db)
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)
        _seed_audit_logs(db, 3)

        resp = client.get(f"/api/audit-log/unified?org_id={org.id}", headers=_h(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["cmmc_total"] == 3
        assert data["datapact_total"] == 0
        assert data["datapact_available"] is False
        assert all(e["source"] == "cmmc" for e in data["items"])

    def test_merges_cmmc_and_datapact_logs(self, client, db):
        """When DataPact is available, merges both sources sorted by time."""
        _seed_roles(db)
        org = _make_org(db, api_url="https://datapact.test")
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)
        _seed_audit_logs(db, 2)

        with patch("cmmc.services.unified_audit_service.DataPactClient") as MC:
            mc = AsyncMock()
            mc.get_audit_logs.return_value = MOCK_DP_AUDIT
            MC.return_value = mc

            resp = client.get(f"/api/audit-log/unified?org_id={org.id}", headers=_h(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["cmmc_total"] == 2
        assert data["datapact_total"] == 2
        assert data["datapact_available"] is True
        assert data["total"] == 4

        sources = {e["source"] for e in data["items"]}
        assert sources == {"cmmc", "datapact"}

        # Verify sorted by created_at descending
        dates = [e["created_at"] for e in data["items"]]
        assert dates == sorted(dates, reverse=True)

    def test_datapact_entries_prefixed_with_dp(self, client, db):
        """DataPact entry IDs are prefixed with 'dp-' to avoid collisions."""
        _seed_roles(db)
        org = _make_org(db, api_url="https://datapact.test")
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)

        with patch("cmmc.services.unified_audit_service.DataPactClient") as MC:
            mc = AsyncMock()
            mc.get_audit_logs.return_value = MOCK_DP_AUDIT
            MC.return_value = mc

            resp = client.get(f"/api/audit-log/unified?org_id={org.id}", headers=_h(token))

        dp_entries = [e for e in resp.json()["items"] if e["source"] == "datapact"]
        assert all(e["id"].startswith("dp-") for e in dp_entries)

    def test_filter_by_source_cmmc(self, client, db):
        """source=cmmc returns only local logs."""
        _seed_roles(db)
        org = _make_org(db, api_url="https://datapact.test")
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)
        _seed_audit_logs(db, 2)

        # DataPact should not be called when source=cmmc
        resp = client.get(
            f"/api/audit-log/unified?org_id={org.id}&source=cmmc",
            headers=_h(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(e["source"] == "cmmc" for e in data["items"])
        assert data["datapact_available"] is False

    def test_filter_by_source_datapact(self, client, db):
        """source=datapact returns only DataPact logs."""
        _seed_roles(db)
        org = _make_org(db, api_url="https://datapact.test")
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)
        _seed_audit_logs(db, 2)

        with patch("cmmc.services.unified_audit_service.DataPactClient") as MC:
            mc = AsyncMock()
            mc.get_audit_logs.return_value = MOCK_DP_AUDIT
            MC.return_value = mc

            resp = client.get(
                f"/api/audit-log/unified?org_id={org.id}&source=datapact",
                headers=_h(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["cmmc_total"] == 0
        assert all(e["source"] == "datapact" for e in data["items"])

    def test_filter_by_action(self, client, db):
        """action filter applies to both CMMC and DataPact logs."""
        _seed_roles(db)
        org = _make_org(db, api_url="https://datapact.test")
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)
        _seed_audit_logs(db, 3)

        with patch("cmmc.services.unified_audit_service.DataPactClient") as MC:
            mc = AsyncMock()
            mc.get_audit_logs.return_value = {
                "items": [MOCK_DP_AUDIT["items"][0]],  # only "create" entry
                "total": 1,
            }
            MC.return_value = mc

            resp = client.get(
                f"/api/audit-log/unified?org_id={org.id}&action=create",
                headers=_h(token),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert all(e["action"] == "create" for e in data["items"])

    def test_pagination(self, client, db):
        """limit and offset work across the merged result set."""
        _seed_roles(db)
        org = _make_org(db)
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)
        _seed_audit_logs(db, 5)

        resp = client.get(
            f"/api/audit-log/unified?org_id={org.id}&limit=2&offset=0",
            headers=_h(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2

        # Page 2
        resp = client.get(
            f"/api/audit-log/unified?org_id={org.id}&limit=2&offset=2",
            headers=_h(token),
        )
        assert len(resp.json()["items"]) == 2

    def test_datapact_failure_graceful(self, client, db):
        """If DataPact call fails, returns CMMC logs with datapact_available=False."""
        _seed_roles(db)
        org = _make_org(db, api_url="https://datapact.test")
        admin, token = _make_user(db, ["system_admin"], org_id=org.id)
        _seed_audit_logs(db, 2)

        with patch("cmmc.services.unified_audit_service.DataPactClient") as MC:
            from cmmc.services.datapact_client import DataPactError
            mc = AsyncMock()
            mc.get_audit_logs.side_effect = DataPactError("Connection refused", 503)
            MC.return_value = mc

            resp = client.get(f"/api/audit-log/unified?org_id={org.id}", headers=_h(token))

        assert resp.status_code == 200
        data = resp.json()
        assert data["cmmc_total"] == 2
        assert data["datapact_total"] == 0
        assert data["datapact_available"] is False

    def test_non_admin_forbidden(self, client, db):
        """Viewers cannot access unified audit logs."""
        _seed_roles(db)
        org = _make_org(db)
        viewer, token = _make_user(db, ["viewer"], org_id=org.id)

        resp = client.get(f"/api/audit-log/unified?org_id={org.id}", headers=_h(token))
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client, db):
        """No auth header → 401."""
        resp = client.get("/api/audit-log/unified?org_id=any")
        assert resp.status_code == 401

    def test_org_id_required(self, client, db):
        """org_id is a required query parameter."""
        _seed_roles(db)
        admin, token = _make_user(db, ["system_admin"])

        resp = client.get("/api/audit-log/unified", headers=_h(token))
        assert resp.status_code == 422
