import React from 'react';
import { Home, FolderOpen, Clock, Settings, PanelLeftClose, PanelLeft } from 'lucide-react';

export type NavRoute = 'home' | 'workspace' | 'history' | 'settings';

interface SidebarProps {
  currentRoute: NavRoute;
  onNavigate: (route: NavRoute) => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

const NAV_ITEMS: { route: NavRoute; icon: React.ElementType; label: string }[] = [
  { route: 'home', icon: Home, label: 'Home' },
  { route: 'workspace', icon: FolderOpen, label: 'Workspaces' },
  { route: 'history', icon: Clock, label: 'History' },
  { route: 'settings', icon: Settings, label: 'Settings' },
];

export const Sidebar: React.FC<SidebarProps> = ({ currentRoute, onNavigate, collapsed, onToggleCollapse }) => {
  return (
    <nav className={`sidebar ${collapsed ? 'collapsed' : ''}`} aria-label="Main navigation">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1L12.5 4.5V9.5L7 13L1.5 9.5V4.5L7 1Z" fill="currentColor" />
          </svg>
        </div>
        {!collapsed && <span>Foundation</span>}
      </div>

      <div className="sidebar-nav">
        {NAV_ITEMS.map(({ route, icon: Icon, label }) => (
          <button
            key={route}
            className={`sidebar-nav-item ${currentRoute === route ? 'active' : ''}`}
            onClick={() => onNavigate(route)}
            title={collapsed ? label : undefined}
            aria-current={currentRoute === route ? 'page' : undefined}
          >
            <Icon className="nav-icon" size={18} />
            {!collapsed && <span>{label}</span>}
          </button>
        ))}
      </div>

      <div className="sidebar-footer">
        <button
          className="sidebar-nav-item"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeft className="nav-icon" size={18} /> : <PanelLeftClose className="nav-icon" size={18} />}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </nav>
  );
};
