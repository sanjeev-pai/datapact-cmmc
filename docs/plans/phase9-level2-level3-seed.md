---
prd: "PRD-002-data-model-seed"
title: "Populate Level 2 and Level 3 Practice Seed Data"
description: "Add 93 NIST 800-171 L2 practices and 24 NIST 800-172 L3 practices"
status: DONE
created: 2026-03-03
depends_on: [phase2/seed-data]
---

# Populate Level 2 and Level 3 Practice Seed Data

**Goal:** Populate the CMMC Practice Library with complete Level 2 (NIST SP 800-171 Rev 2) and Level 3 (NIST SP 800-172) practices.

**Sources:**
- Level 2: NIST SP 800-171 Rev 2 — 93 practices (excluding the 17 L1 practices already seeded)
- Level 3: NIST SP 800-172 — 24 enhanced practices per 32 CFR 170.14(c)(4) Table 1

**Totals:**
- L1: 17 practices (existing)
- L2: 93 practices (new) → combined L1+L2 = 110 (full NIST 800-171)
- L3: 24 practices (new)
- Grand total: 134 practices across 14 domains

## Tasks

### Task 1: Populate level2_practices.yaml

93 practices across 14 domains: AC(18), AT(3), AU(9), CM(9), IA(9), IR(3), MA(6), MP(8), PE(2), PS(2), RA(3), CA(4), SC(14), SI(3).

### Task 2: Populate level3_practices.yaml

24 enhanced practices across 10 domains: AC(2), AT(2), CM(3), IA(2), IR(2), PS(1), RA(7), CA(1), SC(1), SI(3).

### Task 3: Update seed tests

Update practice count assertions (17 → 134) and add L2/L3 verification tests.

## Final Validation

- [x] YAML parses correctly with no duplicates
- [x] All 134 practices seed successfully
- [x] Idempotent re-seed works
- [x] All 216 backend + 48 frontend tests pass
