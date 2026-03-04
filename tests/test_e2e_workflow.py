"""End-to-end workflow tests.

Validates the full CMMC compliance workflow through the API layer:
  register → login → create org → create assessment → evaluate practices
  → upload evidence → create findings → generate POA&M → dashboard/reports.
"""

import io

from sqlalchemy.orm import Session

from cmmc.models.cmmc_ref import CMMCDomain, CMMCPractice
from cmmc.models.user import Role, User, UserRole
from cmmc.services.auth_service import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_roles(db: Session) -> None:
    """Create all RBAC roles."""
    for name in (
        "system_admin",
        "org_admin",
        "compliance_officer",
        "assessor",
        "c3pao_lead",
        "viewer",
    ):
        if not db.query(Role).filter(Role.name == name).first():
            db.add(Role(name=name))
    db.commit()


def _seed_cmmc_data(db: Session) -> None:
    """Create minimal CMMC reference data — 1 domain, 3 Level-1 practices."""
    domain = CMMCDomain(domain_id="AC", name="Access Control", description="AC domain")
    db.add(domain)
    db.flush()

    for i in range(1, 4):
        db.add(
            CMMCPractice(
                practice_id=f"AC.L1-b.1.{i:03d}",
                domain_ref="AC",
                title=f"AC practice {i}",
                description=f"Description for AC practice {i}",
                level=1,
            )
        )
    db.commit()


def _make_admin(db: Session, username="admin", email="admin@test.com") -> tuple[User, str]:
    """Create a system_admin user and return (user, access_token)."""
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("password123"),
    )
    db.add(user)
    db.flush()

    role = db.query(Role).filter(Role.name == "system_admin").first()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, ["system_admin"])
    return user, token


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ===========================================================================
# Full Workflow
# ===========================================================================


class TestFullWorkflow:
    """Walk through the complete assessment lifecycle via the HTTP API."""

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def test_01_register_user(self, client, db):
        _seed_roles(db)
        resp = client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@acme.com", "password": "securepass1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "alice"
        assert data["is_active"] is True

    def test_02_login(self, client, db):
        _seed_roles(db)
        client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@acme.com", "password": "securepass1"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "securepass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_03_refresh_token(self, client, db):
        _seed_roles(db)
        client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@acme.com", "password": "securepass1"},
        )
        login = client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "securepass1"},
        ).json()

        resp = client.post(
            "/api/auth/refresh",
            json={"refresh_token": login["refresh_token"]},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    # ------------------------------------------------------------------
    # Org setup (requires system_admin)
    # ------------------------------------------------------------------

    def test_04_create_org(self, client, db):
        _seed_roles(db)
        _, token = _make_admin(db)
        resp = client.post(
            "/api/organizations",
            json={"name": "Acme Corp", "cage_code": "1A2B3", "target_level": 1},
            headers=_auth(token),
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "Acme Corp"

    def test_05_assign_user_to_org_and_role(self, client, db):
        """Register user, create org, assign user to org with assessor role."""
        _seed_roles(db)
        admin, admin_token = _make_admin(db)

        # Register regular user
        reg = client.post(
            "/api/auth/register",
            json={"username": "bob", "email": "bob@acme.com", "password": "securepass1"},
        ).json()

        # Create org
        org = client.post(
            "/api/organizations",
            json={"name": "Acme Corp", "target_level": 1},
            headers=_auth(admin_token),
        ).json()

        # Assign user to org with compliance_officer role
        resp = client.patch(
            f"/api/users/{reg['id']}",
            json={"org_id": org["id"], "roles": ["compliance_officer"]},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["org_id"] == org["id"]
        assert "compliance_officer" in data["roles"]

    # ------------------------------------------------------------------
    # Assessment lifecycle
    # ------------------------------------------------------------------

    def test_06_full_assessment_lifecycle(self, client, db):
        """Create → start → evaluate → upload evidence → submit → complete."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        # Create org
        org = client.post(
            "/api/organizations",
            json={"name": "Acme Corp", "target_level": 1},
            headers=_auth(admin_token),
        ).json()

        # Assign admin to org so org-scoped queries work
        admin.org_id = org["id"]
        db.commit()

        # Create assessment (auto-populates practices for target level)
        assessment = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "Annual Self-Assessment",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()
        assert assessment["status"] == "draft"
        assessment_id = assessment["id"]

        # List assessments
        listing = client.get(
            "/api/assessments",
            headers=_auth(admin_token),
        ).json()
        assert listing["total"] >= 1

        # Start assessment (draft → in_progress)
        resp = client.post(
            f"/api/assessments/{assessment_id}/start",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

        # List practices
        practices = client.get(
            f"/api/assessments/{assessment_id}/practices",
            headers=_auth(admin_token),
        ).json()
        assert len(practices) == 3  # 3 Level-1 practices seeded

        practice_ids = [p["practice_id"] for p in practices]

        # Evaluate practices
        # Practice 1: met
        resp = client.patch(
            f"/api/assessments/{assessment_id}/practices/{practice_ids[0]}",
            json={"status": "met", "score": 1.0, "assessor_notes": "Fully implemented"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "met"

        # Practice 2: not_met
        resp = client.patch(
            f"/api/assessments/{assessment_id}/practices/{practice_ids[1]}",
            json={"status": "not_met", "score": 0.0, "assessor_notes": "Missing controls"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_met"

        # Practice 3: partially_met
        resp = client.patch(
            f"/api/assessments/{assessment_id}/practices/{practice_ids[2]}",
            json={"status": "partially_met", "score": 0.5},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200

        # Upload evidence for practice 1
        ap_id = practices[0]["id"]
        resp = client.post(
            "/api/evidence",
            data={
                "assessment_practice_id": ap_id,
                "title": "Access Control Policy",
                "description": "Corporate AC policy document",
            },
            files={"file": ("policy.pdf", io.BytesIO(b"PDF content here"), "application/pdf")},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 201
        evidence = resp.json()
        assert evidence["review_status"] == "pending"
        evidence_id = evidence["id"]

        # Review evidence (accept)
        resp = client.post(
            f"/api/evidence/{evidence_id}/review",
            json={"review_status": "accepted"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["review_status"] == "accepted"

        # Submit assessment (in_progress → under_review)
        resp = client.post(
            f"/api/assessments/{assessment_id}/submit",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "under_review"

        # Complete assessment (under_review → completed)
        resp = client.post(
            f"/api/assessments/{assessment_id}/complete",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        completed = resp.json()
        assert completed["status"] == "completed"

        # Verify scoring was calculated
        detail = client.get(
            f"/api/assessments/{assessment_id}",
            headers=_auth(admin_token),
        ).json()
        assert detail["status"] == "completed"

    # ------------------------------------------------------------------
    # Findings & POA&M
    # ------------------------------------------------------------------

    def test_07_findings_and_poam(self, client, db):
        """Create findings from assessment → generate POA&M → manage items."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        # Setup: org + completed assessment
        org = client.post(
            "/api/organizations",
            json={"name": "Acme Corp", "target_level": 1},
            headers=_auth(admin_token),
        ).json()
        admin.org_id = org["id"]
        db.commit()

        assessment = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "Q1 Assessment",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()
        assessment_id = assessment["id"]

        # Move through lifecycle
        client.post(f"/api/assessments/{assessment_id}/start", headers=_auth(admin_token))

        practices = client.get(
            f"/api/assessments/{assessment_id}/practices",
            headers=_auth(admin_token),
        ).json()

        # Evaluate all as not_met
        for p in practices:
            client.patch(
                f"/api/assessments/{assessment_id}/practices/{p['practice_id']}",
                json={"status": "not_met", "score": 0.0},
                headers=_auth(admin_token),
            )

        client.post(f"/api/assessments/{assessment_id}/submit", headers=_auth(admin_token))
        client.post(f"/api/assessments/{assessment_id}/complete", headers=_auth(admin_token))

        # Create findings
        finding1 = client.post(
            "/api/findings",
            json={
                "assessment_id": assessment_id,
                "practice_id": practices[0]["practice_id"],
                "finding_type": "deficiency",
                "severity": "high",
                "title": "No access control policy",
                "description": "Organization lacks formal access control policy",
            },
            headers=_auth(admin_token),
        ).json()
        assert finding1["status"] == "open"

        finding2 = client.post(
            "/api/findings",
            json={
                "assessment_id": assessment_id,
                "practice_id": practices[1]["practice_id"],
                "finding_type": "observation",
                "severity": "medium",
                "title": "Weak password policy",
            },
            headers=_auth(admin_token),
        ).json()

        # List findings
        findings_list = client.get(
            f"/api/findings?assessment_id={assessment_id}",
            headers=_auth(admin_token),
        ).json()
        assert findings_list["total"] == 2

        # Create POA&M
        poam = client.post(
            "/api/poams",
            json={
                "org_id": org["id"],
                "assessment_id": assessment_id,
                "title": "Q1 Remediation Plan",
            },
            headers=_auth(admin_token),
        ).json()
        assert poam["status"] == "draft"
        poam_id = poam["id"]

        # Auto-generate POA&M items from findings
        items = client.post(
            f"/api/poams/generate/{assessment_id}?poam_id={poam_id}",
            headers=_auth(admin_token),
        ).json()
        assert len(items) >= 2

        # Add manual POA&M item
        manual_item = client.post(
            f"/api/poams/{poam_id}/items",
            json={
                "practice_id": practices[2]["practice_id"],
                "milestone": "Implement MFA",
                "scheduled_completion": "2026-06-30",
                "resources_required": "IT team, budget for MFA solution",
            },
            headers=_auth(admin_token),
        ).json()
        assert manual_item["milestone"] == "Implement MFA"

        # Get POA&M detail (includes items)
        poam_detail = client.get(
            f"/api/poams/{poam_id}",
            headers=_auth(admin_token),
        ).json()
        assert len(poam_detail["items"]) >= 3

        # Activate POA&M (draft → active)
        resp = client.post(
            f"/api/poams/{poam_id}/activate",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        # Update item status
        item_id = poam_detail["items"][0]["id"]
        resp = client.patch(
            f"/api/poams/{poam_id}/items/{item_id}",
            json={"status": "in_progress"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "in_progress"

    # ------------------------------------------------------------------
    # Dashboard & Reports
    # ------------------------------------------------------------------

    def test_08_dashboard_endpoints(self, client, db):
        """Verify dashboard returns data after assessment completion."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        org = client.post(
            "/api/organizations",
            json={"name": "Acme Corp", "target_level": 1},
            headers=_auth(admin_token),
        ).json()
        admin.org_id = org["id"]
        db.commit()

        # Create and complete assessment
        assessment = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "Dashboard Test",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()
        assessment_id = assessment["id"]

        client.post(f"/api/assessments/{assessment_id}/start", headers=_auth(admin_token))

        practices = client.get(
            f"/api/assessments/{assessment_id}/practices",
            headers=_auth(admin_token),
        ).json()
        for p in practices:
            client.patch(
                f"/api/assessments/{assessment_id}/practices/{p['practice_id']}",
                json={"status": "met", "score": 1.0},
                headers=_auth(admin_token),
            )

        client.post(f"/api/assessments/{assessment_id}/submit", headers=_auth(admin_token))
        client.post(f"/api/assessments/{assessment_id}/complete", headers=_auth(admin_token))

        # Dashboard summary
        resp = client.get("/api/dashboard/summary", headers=_auth(admin_token))
        assert resp.status_code == 200

        # Domain compliance
        resp = client.get(
            f"/api/dashboard/domain-compliance/{assessment_id}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200

        # SPRS history
        resp = client.get(
            f"/api/dashboard/sprs-history/{org['id']}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200

        # Timeline
        resp = client.get(
            f"/api/dashboard/timeline/{org['id']}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200

        # Create a finding for findings-summary
        client.post(
            "/api/findings",
            json={
                "assessment_id": assessment_id,
                "finding_type": "observation",
                "severity": "low",
                "title": "Minor observation",
            },
            headers=_auth(admin_token),
        )

        resp = client.get(
            f"/api/dashboard/findings-summary/{assessment_id}",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200

    def test_09_report_generation(self, client, db):
        """Generate assessment report after completion."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        org = client.post(
            "/api/organizations",
            json={"name": "Acme Corp", "target_level": 1},
            headers=_auth(admin_token),
        ).json()
        admin.org_id = org["id"]
        db.commit()

        assessment = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "Report Test",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()
        assessment_id = assessment["id"]

        client.post(f"/api/assessments/{assessment_id}/start", headers=_auth(admin_token))
        practices = client.get(
            f"/api/assessments/{assessment_id}/practices",
            headers=_auth(admin_token),
        ).json()
        for p in practices:
            client.patch(
                f"/api/assessments/{assessment_id}/practices/{p['practice_id']}",
                json={"status": "met", "score": 1.0},
                headers=_auth(admin_token),
            )
        client.post(f"/api/assessments/{assessment_id}/submit", headers=_auth(admin_token))
        client.post(f"/api/assessments/{assessment_id}/complete", headers=_auth(admin_token))

        # CSV report
        resp = client.get(
            f"/api/reports/assessment/{assessment_id}?format=csv",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 200


# ===========================================================================
# Org Isolation
# ===========================================================================


class TestOrgIsolation:
    """Verify that users cannot access other organizations' data."""

    def test_user_cannot_access_other_org_assessment(self, client, db):
        _seed_roles(db)
        _seed_cmmc_data(db)

        # Admin creates two orgs
        admin, admin_token = _make_admin(db)

        org_a = client.post(
            "/api/organizations",
            json={"name": "Org A"},
            headers=_auth(admin_token),
        ).json()
        org_b = client.post(
            "/api/organizations",
            json={"name": "Org B"},
            headers=_auth(admin_token),
        ).json()

        # Create user in Org A with assessor role
        user_a = User(
            username="user_a",
            email="user_a@orga.com",
            password_hash=hash_password("password123"),
            org_id=org_a["id"],
        )
        db.add(user_a)
        db.flush()
        role = db.query(Role).filter(Role.name == "assessor").first()
        db.add(UserRole(user_id=user_a.id, role_id=role.id))
        db.commit()
        db.refresh(user_a)
        token_a = create_access_token(user_a.id, ["assessor"])

        # Admin creates assessment in Org B
        assessment_b = client.post(
            "/api/assessments",
            json={
                "org_id": org_b["id"],
                "title": "Org B Assessment",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()

        # User A tries to access Org B's assessment → 403
        resp = client.get(
            f"/api/assessments/{assessment_b['id']}",
            headers=_auth(token_a),
        )
        assert resp.status_code == 403

    def test_user_cannot_access_other_org_findings(self, client, db):
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        org_a = client.post(
            "/api/organizations", json={"name": "Org A"}, headers=_auth(admin_token)
        ).json()
        org_b = client.post(
            "/api/organizations", json={"name": "Org B"}, headers=_auth(admin_token)
        ).json()

        # Assessment in Org B
        assessment_b = client.post(
            "/api/assessments",
            json={
                "org_id": org_b["id"],
                "title": "Org B Assessment",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()

        # Finding in Org B's assessment
        finding = client.post(
            "/api/findings",
            json={
                "assessment_id": assessment_b["id"],
                "finding_type": "deficiency",
                "severity": "high",
                "title": "Secret finding",
            },
            headers=_auth(admin_token),
        ).json()

        # User in Org A
        user_a = User(
            username="user_a",
            email="user_a@orga.com",
            password_hash=hash_password("password123"),
            org_id=org_a["id"],
        )
        db.add(user_a)
        db.flush()
        role = db.query(Role).filter(Role.name == "assessor").first()
        db.add(UserRole(user_id=user_a.id, role_id=role.id))
        db.commit()
        db.refresh(user_a)
        token_a = create_access_token(user_a.id, ["assessor"])

        # User A tries to access Org B's finding → 403
        resp = client.get(
            f"/api/findings/{finding['id']}",
            headers=_auth(token_a),
        )
        assert resp.status_code == 403


# ===========================================================================
# Role Restrictions
# ===========================================================================


class TestRoleRestrictions:
    """Verify that viewers cannot perform write operations."""

    def test_viewer_cannot_create_assessment(self, client, db):
        _seed_roles(db)
        _seed_cmmc_data(db)

        # Create org via admin
        admin, admin_token = _make_admin(db)
        org = client.post(
            "/api/organizations",
            json={"name": "ViewerOrg"},
            headers=_auth(admin_token),
        ).json()

        # Create viewer user in org
        viewer = User(
            username="viewer_user",
            email="viewer@test.com",
            password_hash=hash_password("password123"),
            org_id=org["id"],
        )
        db.add(viewer)
        db.flush()
        role = db.query(Role).filter(Role.name == "viewer").first()
        db.add(UserRole(user_id=viewer.id, role_id=role.id))
        db.commit()
        db.refresh(viewer)
        viewer_token = create_access_token(viewer.id, ["viewer"])

        # Viewer tries to create assessment → 403
        resp = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "Should Fail",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(viewer_token),
        )
        assert resp.status_code == 403

    def test_viewer_cannot_create_org(self, client, db):
        _seed_roles(db)
        viewer = User(
            username="viewer_user",
            email="viewer@test.com",
            password_hash=hash_password("password123"),
        )
        db.add(viewer)
        db.flush()
        role = db.query(Role).filter(Role.name == "viewer").first()
        db.add(UserRole(user_id=viewer.id, role_id=role.id))
        db.commit()
        db.refresh(viewer)
        viewer_token = create_access_token(viewer.id, ["viewer"])

        resp = client.post(
            "/api/organizations",
            json={"name": "Should Fail"},
            headers=_auth(viewer_token),
        )
        assert resp.status_code == 403

    def test_unauthenticated_request_rejected(self, client, db):
        resp = client.get("/api/assessments")
        assert resp.status_code == 401


# ===========================================================================
# Status Transition Enforcement
# ===========================================================================


class TestStatusTransitions:
    """Verify invalid status transitions are rejected."""

    def test_cannot_skip_to_under_review(self, client, db):
        """Cannot submit a draft assessment (must start first)."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        org = client.post(
            "/api/organizations",
            json={"name": "TransOrg"},
            headers=_auth(admin_token),
        ).json()
        admin.org_id = org["id"]
        db.commit()

        assessment = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "Draft Assessment",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()

        # Try to submit a draft → should fail
        resp = client.post(
            f"/api/assessments/{assessment['id']}/submit",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 409

    def test_cannot_complete_in_progress(self, client, db):
        """Cannot complete an in_progress assessment (must submit first)."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        org = client.post(
            "/api/organizations",
            json={"name": "TransOrg"},
            headers=_auth(admin_token),
        ).json()
        admin.org_id = org["id"]
        db.commit()

        assessment = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "In Progress Assessment",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()

        client.post(
            f"/api/assessments/{assessment['id']}/start",
            headers=_auth(admin_token),
        )

        # Try to complete in_progress → should fail
        resp = client.post(
            f"/api/assessments/{assessment['id']}/complete",
            headers=_auth(admin_token),
        )
        assert resp.status_code == 409

    def test_cannot_update_completed_assessment(self, client, db):
        """Cannot modify a completed assessment."""
        _seed_roles(db)
        _seed_cmmc_data(db)
        admin, admin_token = _make_admin(db)

        org = client.post(
            "/api/organizations",
            json={"name": "TransOrg"},
            headers=_auth(admin_token),
        ).json()
        admin.org_id = org["id"]
        db.commit()

        assessment = client.post(
            "/api/assessments",
            json={
                "org_id": org["id"],
                "title": "Will Complete",
                "target_level": 1,
                "assessment_type": "self",
            },
            headers=_auth(admin_token),
        ).json()
        aid = assessment["id"]

        client.post(f"/api/assessments/{aid}/start", headers=_auth(admin_token))
        client.post(f"/api/assessments/{aid}/submit", headers=_auth(admin_token))
        client.post(f"/api/assessments/{aid}/complete", headers=_auth(admin_token))

        # Try to update completed → should fail
        resp = client.patch(
            f"/api/assessments/{aid}",
            json={"title": "New Title"},
            headers=_auth(admin_token),
        )
        assert resp.status_code == 409
