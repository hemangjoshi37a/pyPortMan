import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { path: '/', icon: '📊', label: 'Dashboard', key: 'dashboard' },
  { path: '/accounts', icon: '👤', label: 'Accounts', key: 'accounts' },
  { path: '/holdings', icon: '📈', label: 'Holdings', key: 'holdings' },
  { path: '/orders', icon: '📋', label: 'Orders', key: 'orders' },
  { path: '/gtt', icon: '⚡', label: 'GTT Orders', key: 'gtt' },
  { path: '/positions', icon: '🎯', label: 'Positions', key: 'positions' },
  { path: '/settings', icon: '⚙️', label: 'Settings', key: 'settings' }
];

export default function Sidebar() {
  const location = useLocation();

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-icon">📊</div>
      </div>
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
            title={item.label}
          >
            <span className="nav-icon">{item.icon}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
