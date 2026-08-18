import React, { useState, useCallback } from 'react';
import { Sidebar, type NavRoute } from './Sidebar';
import { useWorkspaceStore } from '../../state/workspaceStore';

// Lazy imports — pages
import { HomePage } from '../../pages/HomePage';
import { WorkspaceView } from '../workspace/WorkspaceView';

export const AppShell: React.FC = () => {
  const { currentView, setCurrentView } = useWorkspaceStore();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Map workspace store's currentView to sidebar's NavRoute
  const activeRoute: NavRoute = (() => {
    switch (currentView) {
      case 'home': return 'home';
      case 'workspace': return 'workspace';
      case 'history': return 'history';
      case 'settings': return 'settings';
      default: return 'home';
    }
  })();

  // Workspace always opens WorkspaceView, with or without documents — the
  // Workspace itself decides whether to show an empty state or document
  // context. There is no separate upload page to route through first.
  const handleNavigate = useCallback((route: NavRoute) => {
    setCurrentView(route);
  }, [setCurrentView]);

  const renderPage = () => {
    switch (currentView) {
      case 'home':
        return <HomePage />;
      case 'workspace':
        return <WorkspaceView />;
      case 'history':
        return (
          <div className="empty-state">
            <div className="empty-title">History</div>
            <div className="empty-description">Task history will be available in a future update.</div>
          </div>
        );
      case 'settings':
        return (
          <div className="empty-state">
            <div className="empty-title">Settings</div>
            <div className="empty-description">Settings will be available in a future update.</div>
          </div>
        );
      default:
        return <HomePage />;
    }
  };

  return (
    <div className="app-shell">
      <Sidebar
        currentRoute={activeRoute}
        onNavigate={handleNavigate}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <main className="app-main">
        {renderPage()}
      </main>
    </div>
  );
};
