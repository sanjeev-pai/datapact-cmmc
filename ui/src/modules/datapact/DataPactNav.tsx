import { NavLink } from 'react-router-dom'

const TABS = [
  { to: '/datapact', label: 'Settings', end: true },
  { to: '/datapact/mappings', label: 'Practice Mappings', end: false },
]

export default function DataPactNav() {
  return (
    <div className="tabs tabs-bordered mb-4">
      {TABS.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.end}
          className={({ isActive }) =>
            `tab ${isActive ? 'tab-active' : ''}`
          }
        >
          {tab.label}
        </NavLink>
      ))}
    </div>
  )
}
