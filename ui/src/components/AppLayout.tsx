import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import OrgSelector from '@/components/OrgSelector'

interface NavItem {
  to: string
  label: string
  icon: string
  roles?: string[]
  /** When true, any path starting with `to` will highlight this item */
  matchPrefix?: boolean
}

interface NavSection {
  title: string
  items: NavItem[]
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Overview',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: '◉' },
    ],
  },
  {
    title: 'Compliance',
    items: [
      { to: '/cmmc', label: 'CMMC Library', icon: '◎' },
      { to: '/assessments', label: 'Assessments', icon: '◈', matchPrefix: true },
      { to: '/evidence', label: 'Evidence', icon: '◆' },
      { to: '/findings', label: 'Findings', icon: '▲' },
      { to: '/poams', label: 'POA&M', icon: '▧', matchPrefix: true },
    ],
  },
  {
    title: 'Integration',
    items: [
      { to: '/datapact', label: 'DataPact', icon: '⬡', matchPrefix: true },
      { to: '/reports', label: 'Reports', icon: '▤' },
    ],
  },
  {
    title: 'System',
    items: [
      { to: '/admin', label: 'Admin', icon: '⚙', roles: ['system_admin', 'org_admin'] },
    ],
  },
]

export default function AppLayout() {
  const { user, logout, hasRole } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  function isItemActive(item: NavItem): boolean {
    if (location.pathname === item.to) return true
    if (item.matchPrefix && location.pathname.startsWith(item.to + '/')) return true
    return false
  }

  return (
    <div className="flex h-screen bg-base-200">
      {/* Sidebar */}
      <aside className="w-64 bg-base-100 border-r border-base-300 flex flex-col">
        <div className="p-4 border-b border-base-300">
          <h1 className="text-lg font-bold text-primary">CMMC Tracker</h1>
          <p className="text-xs text-base-content/50">Compliance Platform</p>
        </div>
        <OrgSelector />
        <nav className="flex-1 overflow-y-auto p-2 space-y-4">
          {NAV_SECTIONS.map((section) => {
            const visibleItems = section.items.filter(
              (item) => !item.roles || hasRole(...item.roles),
            )
            if (visibleItems.length === 0) return null
            return (
              <div key={section.title}>
                <p className="px-3 py-1 text-xs font-semibold text-base-content/40 uppercase tracking-wider">
                  {section.title}
                </p>
                {visibleItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={() =>
                      `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                        isItemActive(item)
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'text-base-content/70 hover:bg-base-200'
                      }`
                    }
                  >
                    <span className="text-base w-5 text-center">{item.icon}</span>
                    {item.label}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>
        <div className="border-t border-base-300 p-3">
          {user && (
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{user.username}</p>
                <p className="text-xs text-base-content/50 truncate">{user.email}</p>
              </div>
              <button
                onClick={handleLogout}
                className="btn btn-ghost btn-xs"
                aria-label="Log out"
              >
                ↪
              </button>
            </div>
          )}
        </div>
        <div className="px-4 pb-3 text-xs text-base-content/40">
          v0.1.0
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
