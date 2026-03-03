import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from '@/components/AppLayout'
import ProtectedRoute from '@/components/ProtectedRoute'
import { AuthProvider } from '@/contexts/AuthContext'
import AssessmentCreatePage from '@/modules/assessments/AssessmentCreatePage'
import AssessmentListPage from '@/modules/assessments/AssessmentListPage'
import AssessmentWorkspacePage from '@/modules/assessments/AssessmentWorkspacePage'
import CMMCLibraryPage from '@/modules/cmmc/CMMCLibraryPage'
import DataPactSettingsPage from '@/modules/datapact/DataPactSettingsPage'
import EvidenceListPage from '@/modules/evidence/EvidenceListPage'
import LoginPage from '@/modules/auth/LoginPage'
import RegisterPage from '@/modules/auth/RegisterPage'

// Placeholder pages — will be replaced in subsequent phases
function DashboardPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      <p className="text-base-content/70">Compliance overview coming in Phase 7.</p>
    </div>
  )
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/cmmc" element={<CMMCLibraryPage />} />
              <Route path="/assessments" element={<AssessmentListPage />} />
              <Route path="/assessments/new" element={<AssessmentCreatePage />} />
              <Route path="/assessments/:id" element={<AssessmentWorkspacePage />} />
              <Route path="/evidence" element={<EvidenceListPage />} />
              <Route path="/datapact" element={<DataPactSettingsPage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
