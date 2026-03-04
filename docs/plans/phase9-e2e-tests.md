# Plan: phase9/e2e-tests

## Approach
Single test file `tests/test_e2e_workflow.py` with ordered test methods in a class. Tests share state via class attributes to build up the workflow incrementally. Each test depends on prior tests having run.

## Test Structure

```
class TestFullWorkflow:
    # Auth
    test_01_register_user
    test_02_login
    test_03_refresh_token

    # Org setup
    test_04_create_organization
    test_05_assign_user_to_org

    # CMMC reference data
    test_06_seed_practices
    test_07_browse_cmmc_library

    # Assessment lifecycle
    test_08_create_assessment
    test_09_start_assessment
    test_10_list_assessment_practices
    test_11_evaluate_practice_met
    test_12_evaluate_practice_not_met

    # Evidence
    test_13_upload_evidence
    test_14_review_evidence

    # Complete assessment
    test_15_submit_assessment
    test_16_complete_assessment
    test_17_verify_scoring

    # Findings
    test_18_create_finding

    # POA&M
    test_19_generate_poam_from_findings
    test_20_add_poam_item
    test_21_activate_poam

    # Dashboard & Reports
    test_22_dashboard_summary
    test_23_generate_report

class TestOrgIsolation:
    # Verify users in org A can't access org B's data

class TestRoleRestrictions:
    # Verify viewer can't create assessments, etc.
```

## Implementation
- Single file, ~400 lines
- Reuse conftest.py fixtures (db, client)
- Helper functions for seeding reference data
- Class-level state via `pytest` class attributes
