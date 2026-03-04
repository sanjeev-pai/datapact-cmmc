import { useContext } from 'react'
import { OrgContext } from '@/contexts/OrgContext'
import type { OrgContextValue } from '@/contexts/OrgContext'

export function useOrg(): OrgContextValue {
  const ctx = useContext(OrgContext)
  if (!ctx) {
    throw new Error('useOrg must be used within an OrgProvider')
  }
  return ctx
}
