import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '@/components/AppLayout'

// Placeholder pages — will be replaced in subsequent phases
function DashboardPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <p className="text-base-content/70">Compliance overview coming in Phase 7.</p>
    </div>
  )
}

function CMMCLibraryPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">CMMC Practice Library</h1>
      <p className="text-base-content/70">Browse all CMMC practices — coming in Phase 2.</p>
    </div>
  )
}

function AssessmentsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Assessments</h1>
      <p className="text-base-content/70">Assessment workflow — coming in Phase 4.</p>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/cmmc" element={<CMMCLibraryPage />} />
          <Route path="/assessments" element={<AssessmentsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
