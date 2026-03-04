# Plan: phase9/error-handling

## Goal
Implement global error handling UX across backend and frontend for consistent error responses, user-facing notifications, and graceful failure recovery.

## Changes

### Backend (`cmmc/app.py`)
- **RequestValidationError handler**: Returns 422 with `{detail, error_code: "VALIDATION_ERROR", errors}` format
- **Unhandled Exception handler**: Returns 500 with `{detail: "An internal server error occurred.", error_code: "INTERNAL_ERROR"}`, logs full traceback

### Frontend
- **react-hot-toast**: Installed as toast notification library
- **`ErrorBoundary`** (`ui/src/components/ErrorBoundary.tsx`): React error boundary catching component crashes, shows error card with Refresh/Try Again buttons
- **`NotFoundPage`** (`ui/src/components/NotFoundPage.tsx`): 404 page with navigation back to dashboard
- **`useApiErrorHandler`** (`ui/src/hooks/useApiErrorHandler.ts`): Hook for pages to handle API errors with toast notifications (skips 401s, handles network errors)
- **`App.tsx`**: Added Toaster provider, ErrorBoundary wrapper, catch-all `*` route for 404

### Tests
- Backend: 5 tests for validation error format, 404 handling, health endpoint
- Frontend: 6 tests for ErrorBoundary and NotFoundPage components
