import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

interface NavItem {
  to: string
  label: string
  icon: string
  roles?: string[]
}

const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: '◉' },
  { to: '/cmmc', label: 'CMMC Library', icon: '◎' },
  { to: '/assessments', label: 'Assessments', icon: '◈' },
  { to: '/evidence', label: 'Evidence', icon: '◆' },
  { to: '/findings', label: 'Findings', icon: '▲' },
  { to: '/poams', label: 'POA&M', icon: '▧' },
  { to: '/datapact', label: 'DataPact', icon: '⬡' },
  { to: '/reports', label: 'Reports', icon: '▤' },
  { to: '/admin', label: 'Admin', icon: '⚙', roles: ['system_admin', 'org_admin'] },
]

export default function AppLayout() {
  const { user, logout, hasRole } = useAuth()
  const navigate = useNavigate()

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || hasRole(...item.roles),
  )

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex h-screen bg-base-200">
      {/* Sidebar */}
      <aside className="w-64 bg-base-100 border-r border-base-300 flex flex-col">
        <div className="p-4 border-b border-base-300">
          <h1 className="text-lg font-bold text-primary">CMMC Tracker</h1>
          <p className="text-xs text-base-content/50">Compliance Platform</p>
        </div>
        <nav className="flex-1 p-2">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-base-content/70 hover:bg-base-200'
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
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
