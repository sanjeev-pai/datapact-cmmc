import { Outlet, NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: '◉' },
  { to: '/cmmc', label: 'CMMC Library', icon: '◎' },
  { to: '/assessments', label: 'Assessments', icon: '◈' },
]

export default function AppLayout() {
  return (
    <div className="flex h-screen bg-base-200">
      {/* Sidebar */}
      <aside className="w-64 bg-base-100 border-r border-base-300 flex flex-col">
        <div className="p-4 border-b border-base-300">
          <h1 className="text-lg font-bold text-primary">CMMC Tracker</h1>
          <p className="text-xs text-base-content/50">Compliance Platform</p>
        </div>
        <nav className="flex-1 p-2">
          {NAV_ITEMS.map((item) => (
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
        <div className="p-4 border-t border-base-300 text-xs text-base-content/40">
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
