# PRD-006: DataPact Integration — Deep Delegation

## Overview
Integrate the CMMC tracker with DataPact's contract management platform using a **deep delegation** model. DataPact becomes the source of truth for organizations (tenants), contracts, compliance scoring, and certification data. The CMMC tracker stores only CMMC-specific data locally (practices, assessment workflow state, evidence, findings).

## Goals
- Enable organizations to connect their DataPact instance via API URL + key
- Delegate organization/tenant management to DataPact (create, sync, update)
- Map CMMC practices to DataPact contracts
- Sync compliance data and scoring from DataPact into assessment practice evaluations
- Map DataPact certification tiers to CMMC levels
- Provide visibility into DataPact sync status, compliance scores, and history
- Include DataPact contract compliance data in assessment reports and dashboards

## Architecture: Deep Delegation Model

### What lives in DataPact (source of truth)
- **Tenants/Organizations**: Created and managed in DataPact, linked via `datapact_tenant_id`
- **Contracts**: Full contract CRUD, versioning, lifecycle
- **Compliance Scoring**: Per-contract and org-level scores
- **Certification**: Tier-based certification (bronze/silver/gold/platinum)
- **Audit Logs**: DataPact's audit trail

### What lives in CMMC (local)
- **CMMC Reference Data**: Domains, practices, levels (seeded from YAML)
- **Assessments**: Assessment workflow, practice evaluations, scores
- **Evidence**: Assessment evidence artifacts
- **Findings & POA&Ms**: Deficiency tracking and remediation plans
- **Practice-to-Contract Mappings**: Links between CMMC practices and DataPact contracts
- **Sync Logs**: DataPact sync operation history

## Components

### DataPact Client (`cmmc/services/datapact_client.py`)
Full async HTTP client wrapping DataPact's REST API:

**Contract Methods:**
- `get_contracts(**params)` — list contracts (normalizes `results` → `items`)
- `get_contract(id)` — get a single contract
- `get_contract_compliance(id)` — get compliance data for a contract

**Tenant/Organization Methods:**
- `get_tenants(**params)` — list tenants
- `get_tenant(id)` — get tenant details
- `create_tenant(data)` — create a new tenant
- `update_tenant(id, data)` — update tenant
- `delete_tenant(id)` — delete tenant

**Compliance Scoring Methods:**
- `get_compliance_scores(**params)` — list scores across contracts
- `get_compliance_score(contract_id)` — per-contract score
- `get_org_compliance_score()` — org-level aggregate

**Certification Methods:**
- `get_certifications(**params)` — list certifications
- `get_certification(contract_id)` — per-contract certification
- `evaluate_certifications()` — trigger evaluation

**Audit Methods:**
- `get_audit_logs(**params)` — list audit entries

**HTTP Methods:** GET, POST, PUT, DELETE with typed error handling.

### Organization Sync Service (`cmmc/services/org_sync_service.py`)
Bidirectional synchronization between local organizations and DataPact tenants:
- `create_org_with_datapact()` — create in DataPact first, then local
- `sync_org_from_datapact()` — pull tenant data from DataPact, update local
- `update_org_with_datapact()` — update both sides
- `link_org_to_tenant()` — link existing org to existing tenant

### Mapping Service (`cmmc/services/mapping_service.py`)
Practice-to-contract mapping management with keyword-based auto-suggest.

### Sync Service (`cmmc/services/sync_service.py`)
Enhanced sync that uses both compliance and scoring APIs:
- Fetches contract compliance data
- Fetches compliance scoring for richer insights
- Stores score details in assessor notes
- Maps certification tiers to CMMC levels (bronze→1, silver→2, gold/platinum→3)

### Dashboard Service (`cmmc/services/dashboard_service.py`)
Incorporates DataPact org-level compliance scores:
- `get_datapact_compliance(db, org_id)` — fetches org compliance from DataPact

### Report Service (`cmmc/services/report_service.py`)
Assessment reports include DataPact contract mapping data:
- CSV/PDF reports show mapped DataPact contracts per practice

## DataPact API Surface (Key Endpoints)

DataPact (port 8180) provides:
- **Tenants**: `GET/POST/PUT/DELETE /api/tenants/{id}` — org/tenant management
- **Contracts**: `GET/POST /api/contracts` — CRUD, filtering, versioning
- **Compliance Scoring**: `GET /api/compliance/scores/{contract_id}`, `/api/compliance/scores/org`
- **Certification**: `GET /api/certifications/{contract_id}` — tier-based status
- **Audit**: `GET /api/audit` — audit log entries

**Response Shape**: DataPact uses `results` (not `items`) in list responses. The client normalizes this.

## Configuration
- Global defaults: `DATAPACT_API_URL` (default: `http://localhost:8180`), `DATAPACT_TIMEOUT` (default: 30s) in `cmmc/config.py`
- Per-org overrides: `organizations.datapact_api_url`, `organizations.datapact_api_key`
- Org-tenant link: `organizations.datapact_tenant_id`

## Database Changes
- Added `datapact_tenant_id` (String(128), nullable) to `organizations` table
- Migration: `a3c7e9f1b2d4_add_datapact_tenant_id_to_orgs.py`
