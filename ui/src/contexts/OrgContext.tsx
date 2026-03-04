import { createContext, useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { listOrganizations } from '@/services/organizations'
import type { Organization } from '@/services/organizations'

export interface OrgContextValue {
  /** Currently selected org id, or null for "all orgs" (system_admin only) */
  selectedOrgId: string | null
  /** List of available organizations (populated for system_admin) */
  organizations: Organization[]
  /** Select an org (pass null for "all organizations") */
  selectOrg: (orgId: string | null) => void
  /** Effective org id: for system_admin returns selectedOrgId; for others returns user.org_id */
  effectiveOrgId: string | null
  /** Whether the current user is a system_admin */
  isSystemAdmin: boolean
  /** Name of the currently selected org (or null) */
  selectedOrgName: string | null
}

export const OrgContext = createContext<OrgContextValue | null>(null)

export function OrgProvider({ children }: { children: ReactNode }) {
  const { user, hasRole } = useAuth()
  const isSystemAdmin = hasRole('system_admin')

  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null)

  // Fetch orgs for system_admin users
  useEffect(() => {
    if (!isSystemAdmin || !user) {
      setOrganizations([])
      return
    }

    listOrganizations()
      .then(setOrganizations)
      .catch(() => setOrganizations([]))
  }, [isSystemAdmin, user])

  const selectOrg = useCallback((orgId: string | null) => {
    setSelectedOrgId(orgId)
  }, [])

  const effectiveOrgId = useMemo(() => {
    if (isSystemAdmin) {
      return selectedOrgId // null = all orgs
    }
    return user?.org_id ?? null
  }, [isSystemAdmin, selectedOrgId, user?.org_id])

  const selectedOrgName = useMemo(() => {
    if (!selectedOrgId) return null
    const org = organizations.find((o) => o.id === selectedOrgId)
    return org?.name ?? null
  }, [selectedOrgId, organizations])

  const value = useMemo<OrgContextValue>(
    () => ({
      selectedOrgId,
      organizations,
      selectOrg,
      effectiveOrgId,
      isSystemAdmin,
      selectedOrgName,
    }),
    [selectedOrgId, organizations, selectOrg, effectiveOrgId, isSystemAdmin, selectedOrgName],
  )

  return <OrgContext.Provider value={value}>{children}</OrgContext.Provider>
}
