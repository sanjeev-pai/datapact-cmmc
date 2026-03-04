import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import AppLayout from '@/components/AppLayout'
import ErrorBoundary from '@/components/ErrorBoundary'
import NotFoundPage from '@/components/NotFoundPage'
import ProtectedRoute from '@/components/ProtectedRoute'
import { AuthProvider } from '@/contexts/AuthContext'
import AssessmentCreatePage from '@/modules/assessments/AssessmentCreatePage'
import AssessmentListPage from '@/modules/assessments/AssessmentListPage'
import AssessmentWorkspacePage from '@/modules/assessments/AssessmentWorkspacePage'
import CMMCLibraryPage from '@/modules/cmmc/CMMCLibraryPage'
import DataPactMappingsPage from '@/modules/datapact/DataPactMappingsPage'
import DataPactSettingsPage from '@/modules/datapact/DataPactSettingsPage'
import EvidenceListPage from '@/modules/evidence/EvidenceListPage'
import FindingsPage from '@/modules/findings/FindingsPage'
import POAMListPage from '@/modules/poam/POAMListPage'
import POAMKanbanPage from '@/modules/poam/POAMKanbanPage'
import POAMDetailPage from '@/modules/poam/POAMDetailPage'
import AdminPage from '@/modules/admin/AdminPage'
import ReportsPage from '@/modules/reports/ReportsPage'
import DashboardPage from '@/modules/dashboard/DashboardPage'
import LoginPage from '@/modules/auth/LoginPage'
import RegisterPage from '@/modules/auth/RegisterPage'

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: { maxWidth: 420 },
              error: { duration: 5000 },
            }}
          />
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
                <Route path="/findings" element={<FindingsPage />} />
                <Route path="/poams" element={<POAMListPage />} />
                <Route path="/poams/:id" element={<POAMKanbanPage />} />
                <Route path="/poams/:id/detail" element={<POAMDetailPage />} />
                <Route path="/datapact" element={<DataPactSettingsPage />} />
                <Route path="/datapact/mappings" element={<DataPactMappingsPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/admin" element={<AdminPage />} />
              </Route>
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
