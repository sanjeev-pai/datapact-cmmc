import { useOrg } from '@/hooks/useOrg'

export default function OrgSelector() {
  const { isSystemAdmin, organizations, selectedOrgId, selectOrg } = useOrg()

  if (!isSystemAdmin) return null

  return (
    <div className="px-3 py-2">
      <label className="text-xs font-semibold text-base-content/40 uppercase tracking-wider">
        Organization
      </label>
      <select
        className="select select-bordered select-sm w-full mt-1"
        value={selectedOrgId ?? ''}
        onChange={(e) => selectOrg(e.target.value || null)}
        aria-label="Select organization"
      >
        <option value="">All Organizations</option>
        {organizations.map((org) => (
          <option key={org.id} value={org.id}>
            {org.name}
          </option>
        ))}
      </select>
    </div>
  )
}
