"""CMMC reference data API endpoint tests."""

from cmmc.models import CMMCDomain, CMMCLevel, CMMCPractice


def _seed_minimal(db):
    """Seed minimal test data."""
    db.add(CMMCDomain(domain_id="AC", name="Access Control", description="Limit access."))
    db.add(CMMCDomain(domain_id="SI", name="System Integrity", description="Monitor flaws."))
    db.flush()

    db.add(CMMCLevel(level=1, name="Foundational", assessment_type="self"))
    db.add(CMMCLevel(level=2, name="Advanced", assessment_type="third_party"))
    db.flush()

    db.add(CMMCPractice(practice_id="AC.L1-3.1.1", domain_ref="AC", level=1, title="Auth Access"))
    db.add(CMMCPractice(practice_id="AC.L1-3.1.2", domain_ref="AC", level=1, title="Transaction Control"))
    db.add(CMMCPractice(practice_id="SI.L1-3.14.1", domain_ref="SI", level=1, title="Flaw Remediation"))
    db.commit()


class TestDomainsEndpoint:
    def test_list_domains(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/domains")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["domain_id"] == "AC"

    def test_list_domains_empty(self, client):
        res = client.get("/api/cmmc/domains")
        assert res.status_code == 200
        assert res.json() == []


class TestLevelsEndpoint:
    def test_list_levels(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/levels")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["level"] == 1


class TestPracticesEndpoint:
    def test_list_all_practices(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/practices")
        assert res.status_code == 200
        assert len(res.json()) == 3

    def test_filter_by_domain(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/practices?domain=AC")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert all(p["domain_ref"] == "AC" for p in data)

    def test_filter_by_level(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/practices?level=1")
        assert res.status_code == 200
        assert len(res.json()) == 3

    def test_search_practices(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/practices?search=flaw")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["practice_id"] == "SI.L1-3.14.1"

    def test_get_single_practice(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/practices/AC.L1-3.1.1")
        assert res.status_code == 200
        data = res.json()
        assert data["practice_id"] == "AC.L1-3.1.1"
        assert data["title"] == "Auth Access"

    def test_get_nonexistent_practice(self, client, db):
        _seed_minimal(db)
        res = client.get("/api/cmmc/practices/XX.FAKE")
        assert res.status_code == 404
