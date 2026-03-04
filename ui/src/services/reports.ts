import { getAccessToken } from './api'

const BASE = '/api'

/**
 * Download an assessment report as PDF or CSV.
 * Uses raw fetch so we can handle the binary blob directly.
 */
export async function downloadAssessmentReport(
  assessmentId: string,
  format: 'pdf' | 'csv',
): Promise<void> {
  const token = getAccessToken()
  const res = await fetch(
    `${BASE}/reports/assessment/${assessmentId}?format=${format}`,
    {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  )

  if (!res.ok) {
    const text = await res.text()
    let detail = `${res.status} ${res.statusText}`
    try {
      const json = JSON.parse(text)
      if (json.detail) detail = json.detail
    } catch {
      // use default
    }
    throw new Error(detail)
  }

  const blob = await res.blob()
  const ext = format === 'pdf' ? 'pdf' : 'csv'
  const mime = format === 'pdf' ? 'application/pdf' : 'text/csv'
  const url = URL.createObjectURL(new Blob([blob], { type: mime }))
  const a = document.createElement('a')
  a.href = url
  a.download = `assessment-${assessmentId}.${ext}`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/**
 * Download SPRS report for an org as CSV.
 */
export async function downloadSprsReport(orgId: string): Promise<void> {
  const token = getAccessToken()
  const res = await fetch(`${BASE}/reports/sprs/${orgId}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  if (!res.ok) {
    const text = await res.text()
    let detail = `${res.status} ${res.statusText}`
    try {
      const json = JSON.parse(text)
      if (json.detail) detail = json.detail
    } catch {
      // use default
    }
    throw new Error(detail)
  }

  const blob = await res.blob()
  const url = URL.createObjectURL(new Blob([blob], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `sprs-${orgId}.csv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
