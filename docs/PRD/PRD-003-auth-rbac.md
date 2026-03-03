---
id: PRD-003
title: "Auth & RBAC"
description: "Authentication, authorization, and role-based access control for the CMMC tracker"
priority: HIGH
status: IN_PROGRESS
created: 2026-03-03
depends_on: [PRD-002]
---

# Auth & RBAC

## Overview

Users need secure authentication and role-based access control to manage CMMC assessments. This phase adds JWT-based auth, user registration/login, organization management, and role-based route protection on both backend and frontend.

## Business Capability

### 1. User Authentication

Users can register, log in, and receive JWT tokens for stateless API authentication. Refresh tokens enable seamless session extension.

### 2. Role-Based Access Control

Six roles (system_admin, org_admin, compliance_officer, assessor, c3pao_lead, viewer) control access to features. Dependencies enforce role checks at the API layer.

### 3. Organization Management

Admins can create and manage organizations. Users belong to organizations, scoping their data access.

### 4. Protected Frontend

React auth context manages JWT lifecycle. Protected routes redirect unauthenticated users. Role-based UI visibility hides unauthorized features.

## Out of Scope

- OAuth/SSO integration
- Multi-factor authentication
- Password reset flow
- Session management (JWT is stateless)

## Success Metrics

### Quality Metrics
- All auth endpoints have comprehensive test coverage
- No auth bypass vulnerabilities

### Operational Metrics
- JWT validation adds <5ms per request
- Token refresh works transparently

### Developer Experience Metrics
- Adding role protection to a new endpoint is a one-line `Depends()` call

## Dependencies

- PRD-002: Data model (User, Role, Organization models must exist)

## Implementation Reference

- `docs/plans/phase3-auth-dependencies.md`
