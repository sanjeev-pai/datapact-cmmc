# Plan: phase5/ui-evidence-upload

## Objective
Add evidence upload component with drag-and-drop, integrate into workspace practice detail panel.

## Components

### Types (`ui/src/types/evidence.ts`)
- Evidence, EvidenceListResponse, ReviewStatus

### API Service (`ui/src/services/evidence.ts`)
- uploadEvidence (FormData/multipart), listEvidence, getEvidence, deleteEvidence, reviewEvidence, getDownloadUrl

### EvidenceUpload (`ui/src/modules/evidence/EvidenceUpload.tsx`)
- Drag-and-drop zone + file picker
- Title (required) and description fields
- Auto-fills title from filename
- Calls uploadEvidence on submit

### EvidenceList (`ui/src/modules/evidence/EvidenceList.tsx`)
- Lists evidence items with status badges, file sizes, download links
- Delete button for pending items (when editable)

### EvidencePanel (`ui/src/modules/evidence/EvidencePanel.tsx`)
- Wraps EvidenceList + EvidenceUpload
- Loads evidence for a given assessment_practice_id
- Manages local state (add/remove items)

### Integration
- Replace evidence placeholder in WorkspacePracticeDetail with EvidencePanel
- Pass evaluation.id as assessmentPracticeId

## Tests
- EvidenceUpload: form rendering, submit, error handling
- EvidenceList: empty state, items, badges, delete buttons, download links
- EvidencePanel: loading, editable/readonly, empty state
