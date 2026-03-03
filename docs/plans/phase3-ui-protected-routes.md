---
prd: "PRD-003-auth-rbac"
title: "Phase 3: UI Protected Routes"
description: "Add route protection, user info in sidebar, and role-based nav visibility"
status: IN_PROGRESS
created: 2026-03-03
depends_on: [phase3/ui-auth-context, phase3/ui-login-page, phase3/ui-register-page]
---

# Phase 3: UI Protected Routes

**Goal:** Protect authenticated routes with redirect to /login, enhance sidebar with user info and logout, add role-based nav visibility.

**Architecture:** ProtectedRoute wrapper component using AuthContext. AppLayout sidebar enhanced with user section and role-conditional nav items.

**Tech Stack:** React Router v6, AuthContext (existing), DaisyUI components.

## Tasks

### Task 1: ProtectedRoute component

**Test:**
```text
- Renders children when user is authenticated
- Redirects to /login when user is not authenticated
- Shows loading spinner while auth state is loading
- Preserves intended destination in redirect (location state)
```

**Implementation:**
1. Create `ui/src/components/ProtectedRoute.tsx`
2. Uses `useAuth()` to check `user` and `loading` state
3. If loading → show spinner
4. If no user → `<Navigate to="/login" state={{ from: location }} replace />`
5. If authenticated → render `<Outlet />`
6. Optionally accept `roles` prop — if user lacks required roles, show 403 message

**Verification:** `cd ui && npx vitest run src/components/ProtectedRoute.test.tsx`

**Commit:** `feat(ui): add ProtectedRoute component with auth redirect`

---

### Task 2: Update App.tsx to use ProtectedRoute

**Test:**
```text
- Unauthenticated user visiting /dashboard is redirected to /login
- Authenticated user can access /dashboard, /cmmc, /assessments
- Login/register pages remain accessible without auth
```

**Implementation:**
1. Import ProtectedRoute in App.tsx
2. Wrap the `<AppLayout />` route with `<ProtectedRoute />`
3. Root redirect / → /dashboard remains outside protection (will redirect through)

**Verification:** `cd ui && npx vitest run src/App.test.tsx`

**Commit:** `feat(ui): wrap app routes with ProtectedRoute`

---

### Task 3: Enhance AppLayout sidebar with user info and logout

**Test:**
```text
- Sidebar displays current user's username
- Logout button calls auth logout and redirects to /login
- Admin nav item only visible for system_admin/org_admin roles
```

**Implementation:**
1. Import `useAuth` and `useNavigate` in AppLayout
2. Add user info section at bottom of sidebar (above version)
3. Add logout button
4. Add `roles` field to NAV_ITEMS — filter items by role
5. Add Admin nav item with roles: ['system_admin', 'org_admin']

**Verification:** `cd ui && npx vitest run src/components/AppLayout.test.tsx`

**Commit:** `feat(ui): add user info, logout button, role-based nav to sidebar`

---

### Task 4: Update LoginPage to redirect after login

**Test:**
```text
- After successful login, redirects to the page user tried to access (from location state)
- If no saved destination, redirects to /dashboard
```

**Implementation:**
1. In LoginPage, read `location.state?.from` after successful login
2. Navigate to that path or fallback to /dashboard

**Verification:** `cd ui && npx vitest run src/modules/auth/LoginPage.test.tsx`

**Commit:** `feat(ui): redirect to intended destination after login`

## Final Validation

- [ ] All frontend tests pass: `cd ui && npm test`
- [ ] Manual test: unauthenticated → redirected to /login
- [ ] Manual test: login → dashboard accessible
- [ ] Manual test: sidebar shows user + logout works
- [ ] Status updated in PRD and plan
