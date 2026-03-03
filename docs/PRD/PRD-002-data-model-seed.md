# PRD-002: CMMC Data Model & Seed

## Overview

Implement all SQLAlchemy models for the CMMC Tracker database, create the initial Alembic migration, populate YAML seed files with complete practice data for all 3 CMMC levels, and build the seed service and CMMC reference data API endpoints.

## Goals

- Complete database schema covering all CMMC entities
- All 14 domains, 17 Level 1, 110 Level 2, and Level 3 practices seeded from YAML
- Idempotent seed service that runs on startup
- REST endpoints to query domains and practices

## Database Schema

### Reference Data Tables

#### cmmc_domains
| Column | Type | Notes |
|--------|------|-------|
| id | String(64) PK | BaseModel UUID |
| domain_id | String(4) UNIQUE | e.g., AC, AT, AU |
| name | String(128) | e.g., "Access Control" |
| description | Text | Domain description |

#### cmmc_levels
| Column | Type | Notes |
|--------|------|-------|
| id | String(64) PK | BaseModel UUID |
| level | Integer UNIQUE | 1, 2, or 3 |
| name | String(64) | e.g., "Foundational" |
| assessment_type | String(32) | self / third_party / government |
| description | Text | Level description |

#### cmmc_practices
| Column | Type | Notes |
|--------|------|-------|
| id | String(64) PK | BaseModel UUID |
| practice_id | String(32) UNIQUE | e.g., AC.L1-3.1.1 |
| domain_id | String(4) FK | → cmmc_domains.domain_id |
| level | Integer | 1, 2, or 3 |
| title | String(256) | Practice title |
| description | Text | Full description |
| assessment_objectives | JSON | List of assessment objective strings |
| evidence_requirements | JSON | List of evidence requirement strings |
| nist_refs | JSON | NIST SP 800-171/172 reference IDs |

### Core Tables (all extend BaseModel)

#### organizations
| Column | Type | Notes |
|--------|------|-------|
| name | String(256) | Org name |
| cage_code | String(8) | DoD CAGE code |
| duns_number | String(16) | DUNS/UEI |
| target_level | Integer | Target CMMC level (1-3) |
| datapact_api_url | String(512) | DataPact API endpoint |
| datapact_api_key | String(512) | Encrypted API key |

#### users
| Column | Type | Notes |
|--------|------|-------|
| username | String(128) UNIQUE | |
| email | String(256) UNIQUE | |
| password_hash | String(512) | bcrypt hash |
| org_id | String(64) FK | → organizations.id |
| is_active | Boolean | Default true |

#### roles / user_roles
- roles: id, name (compliance_officer, assessor, c3pao_lead, org_admin, system_admin, viewer)
- user_roles: user_id FK, role_id FK (junction)

#### assessments
| Column | Type | Notes |
|--------|------|-------|
| org_id | String(64) FK | → organizations.id |
| title | String(256) | Assessment title |
| target_level | Integer | 1, 2, or 3 |
| assessment_type | String(32) | self / third_party / government |
| status | String(32) | draft / in_progress / under_review / completed |
| lead_assessor_id | String(64) FK | → users.id |
| started_at | DateTime | When assessment started |
| completed_at | DateTime | When completed |
| overall_score | Float | Calculated score |
| sprs_score | Integer | SPRS score (-203 to 110) |

#### assessment_practices
| Column | Type | Notes |
|--------|------|-------|
| assessment_id | String(64) FK | → assessments.id |
| practice_id | String(32) FK | → cmmc_practices.practice_id |
| status | String(32) | met / not_met / partially_met / not_applicable / not_evaluated |
| score | Float | 0.0 to 1.0 |
| assessor_notes | Text | |
| datapact_sync_status | String(32) | Suggested status from DataPact |
| datapact_sync_at | DateTime | Last sync timestamp |

#### evidence
| Column | Type | Notes |
|--------|------|-------|
| assessment_practice_id | String(64) FK | → assessment_practices.id |
| title | String(256) | Evidence title |
| description | Text | |
| file_path | String(512) | Local file path |
| file_url | String(512) | External URL |
| review_status | String(32) | pending / accepted / rejected |
| reviewer_id | String(64) FK | → users.id |
| reviewed_at | DateTime | |

#### findings
| Column | Type | Notes |
|--------|------|-------|
| assessment_id | String(64) FK | → assessments.id |
| practice_id | String(32) | Related practice |
| finding_type | String(32) | deficiency / observation / recommendation / strength |
| severity | String(16) | critical / high / medium / low |
| title | String(256) | |
| description | Text | |
| status | String(32) | open / in_remediation / resolved / accepted |

#### poams
| Column | Type | Notes |
|--------|------|-------|
| org_id | String(64) FK | → organizations.id |
| assessment_id | String(64) FK | → assessments.id |
| title | String(256) | POA&M plan title |
| status | String(32) | draft / active / completed |

#### poam_items
| Column | Type | Notes |
|--------|------|-------|
| poam_id | String(64) FK | → poams.id |
| finding_id | String(64) FK | → findings.id |
| practice_id | String(32) | Related practice |
| milestone | String(256) | |
| scheduled_completion | Date | |
| actual_completion | Date | |
| status | String(32) | open / in_progress / completed / overdue |
| resources_required | Text | |
| risk_accepted | Boolean | Default false |

#### datapact_practice_mappings
| Column | Type | Notes |
|--------|------|-------|
| org_id | String(64) FK | → organizations.id |
| practice_id | String(32) FK | → cmmc_practices.practice_id |
| datapact_contract_id | String(128) | DataPact contract ID |
| datapact_contract_name | String(256) | Display name |

#### datapact_sync_logs
| Column | Type | Notes |
|--------|------|-------|
| org_id | String(64) FK | → organizations.id |
| assessment_id | String(64) FK | → assessments.id |
| practice_id | String(32) | |
| request_payload | JSON | |
| response_payload | JSON | |
| status | String(32) | success / error / timeout |
| error_message | Text | |

#### audit_log
| Column | Type | Notes |
|--------|------|-------|
| user_id | String(64) FK | → users.id |
| action | String(64) | e.g., assessment.create |
| resource_type | String(64) | e.g., assessment |
| resource_id | String(64) | |
| details | JSON | |
| ip_address | String(64) | |

## API Endpoints

### GET /api/cmmc/domains
Returns all 14 CMMC domains.

### GET /api/cmmc/practices
Query params: `level` (int), `domain` (str), `search` (str)
Returns filtered list of practices.

### GET /api/cmmc/practices/{practice_id}
Returns single practice detail with assessment objectives and evidence requirements.

### GET /api/cmmc/levels
Returns all 3 levels with descriptions.

## Seed Service

- `cmmc/services/seed_service.py`
- Reads YAML files from `data/cmmc/`
- Idempotent: uses `practice_id` / `domain_id` as natural keys for upsert
- Runs on app startup when `CMMC_AUTO_SEED=true` (default)
- CLI: `python -m cmmc.services.seed_service` for manual seeding

## YAML Data Files

- `data/cmmc/domains.yaml` — 14 domains (already created)
- `data/cmmc/level1_practices.yaml` — 17 practices (already created)
- `data/cmmc/level2_practices.yaml` — 110 practices mapped from NIST SP 800-171 Rev 2
- `data/cmmc/level3_practices.yaml` — Level 3 practices from NIST SP 800-172

## Tests

- `tests/test_models.py` — model instantiation, BaseModel behavior
- `tests/test_seed.py` — seed service loads data correctly, idempotent
- `tests/test_cmmc_api.py` — domain/practice endpoints return correct data

## Verification

1. `make db-upgrade` creates all tables
2. `make db-seed` populates reference data
3. `curl /api/cmmc/domains` returns 14 domains
4. `curl /api/cmmc/practices?level=1` returns 17 practices
5. `make test-backend` passes all tests

## Status

**Pending** — scheduled for Phase 2.
