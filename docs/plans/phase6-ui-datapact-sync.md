# Plan: phase6/ui-datapact-sync — DataPact Sync UI

## Overview
Add sync UI to the assessment workspace so users can sync individual practices or bulk-sync all practices with DataPact, see sync status indicators, and view sync logs.

## Components

### 1. `DataPactSyncPanel` (`ui/src/modules/datapact/DataPactSyncPanel.tsx`)
Collapsible panel added to `WorkspacePracticeDetail` below Evidence. Shows:
- Current sync status badge for the selected practice (`datapact_sync_status` / `datapact_sync_at`)
- "Sync This Practice" button — calls `syncPractice(assessmentId, practiceId)`
- Inline result feedback (success/error message after sync)

### 2. `SyncAllButton` in workspace header
Added to `AssessmentWorkspacePage` header next to status transition buttons.
- "Sync All" button — calls `syncAssessment(assessmentId)`
- Shows progress: "Syncing..." → result summary toast
- On completion, refreshes evaluations to pick up `datapact_sync_status` updates

### 3. `DataPactSyncLogViewer` (`ui/src/modules/datapact/DataPactSyncLogViewer.tsx`)
A collapsible section at the bottom of the sync panel or a separate tab. Shows:
- Recent sync logs for the current assessment (via `getSyncLogs({ assessment_id })`)
- Columns: practice_id, status, error_message, timestamp
- Auto-refreshes after sync operations

### 4. Sync status indicators in practice list
Update `WorkspacePracticeList` to show a small sync status icon next to each practice:
- Green dot = synced
- Red dot = error
- No dot = never synced

## Changes to Existing Files
- `AssessmentWorkspacePage.tsx` — Add "Sync All" button in header, pass assessment ID down, refresh evaluations after sync
- `WorkspacePracticeDetail.tsx` — Add `DataPactSyncPanel` below Evidence section, pass evaluation sync fields + assessmentId
- `WorkspacePracticeList.tsx` — Add sync status dot indicator

## Test Plan
- `DataPactSyncPanel.test.tsx` — Tests for sync button, status display, sync results
- Update `AssessmentWorkspacePage.test.tsx` — Add tests for "Sync All" button
- Mock `syncPractice`, `syncAssessment`, `getSyncLogs` API calls
