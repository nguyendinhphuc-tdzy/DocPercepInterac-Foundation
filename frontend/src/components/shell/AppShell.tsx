import React, { useState, useCallback } from 'react';
import { Sidebar, type NavRoute } from './Sidebar';
import { useWorkspaceStore } from '../../state/workspaceStore';

// Lazy imports — pages
import { HomePage } from '../../pages/HomePage';
import { NewTaskPage } from '../../pages/NewTaskPage';
import { WorkspaceView } from '../workspace/WorkspaceView';

export const AppShell: React.FC = () => {
  const { currentView, setCurrentView } = useWorkspaceStore();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Map workspace store's currentView to sidebar's NavRoute
  const activeRoute: NavRoute = (() => {
    switch (currentView) {
      case 'home': return 'home';
      case 'new-task': return 'home';
      case 'workspace': return 'workspace';
      case 'history': return 'history';
      case 'settings': return 'settings';
      default: return 'home';
    }
  })();

  const handleNavigate = useCallback((route: NavRoute) => {
    if (route === 'home') {
      setCurrentView('home');
    } else if (route === 'workspace') {
      // If we have a process, go to workspace; otherwise go to new task
      const state = useWorkspaceStore.getState();
      if (state.processingStatus === 'done' || state.sourceFiles.length > 0) {
        setCurrentView('workspace');
      } else {
        setCurrentView('new-task');
      }
    } else {
      setCurrentView(route as any);
    }
  }, [setCurrentView]);

  const renderPage = () => {
    switch (currentView) {
      case 'home':
        return <HomePage />;
      case 'new-task':
        return <NewTaskPage />;
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
