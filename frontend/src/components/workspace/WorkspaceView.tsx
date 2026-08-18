import React from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { GitCompare } from 'lucide-react';
import { WorkspaceHeader } from './WorkspaceHeader';
import { FileRail } from './FileRail';
import { AgentPane } from '../agent/AgentPane';
import { ElementsPane } from '../elements/ElementsPane';
import { ResultsPane } from '../results/ResultsPane';
import { DocumentPane } from '../document/DocumentPane';
import { EmptyState } from '../shared/EmptyState';
import { useWorkspaceStore } from '../../state/workspaceStore';

// Workspace is the primary entry surface regardless of document count — it
// decides for itself whether to show an empty state or document context.
// It must never bounce the user to a separate upload page.
export const WorkspaceView: React.FC = () => {
  const { workspacePreset } = useWorkspaceStore();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <WorkspaceHeader />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <FileRail />
        <div style={{ flex: 1, overflow: 'hidden' }}>
          {workspacePreset === 'agent' && <AgentPresetLayout />}
          {workspacePreset === 'inspect' && <InspectPresetLayout />}
          {workspacePreset === 'review' && <ReviewPresetLayout />}
          {workspacePreset === 'compare' && <ComparePresetLayout />}
        </div>
      </div>
    </div>
  );
};

// ── Preset Layouts ── //

/** Agent + Document (default) — Agent is the dominant surface */
const AgentPresetLayout: React.FC = () => (
  <PanelGroup orientation="horizontal">
    <Panel defaultSize={65} minSize={40}>
      <AgentPane />
    </Panel>
    <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />
    <Panel defaultSize={35} minSize={25}>
      <DocumentPane />
    </Panel>
  </PanelGroup>
);

/** Inspect: Document + Elements + Inspector */
const InspectPresetLayout: React.FC = () => (
  <PanelGroup orientation="horizontal">
    <Panel defaultSize={40} minSize={25}>
      <DocumentPane />
    </Panel>
    <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />
    <Panel defaultSize={60} minSize={35}>
      <ElementsPane />
    </Panel>
  </PanelGroup>
);

/** Review: Document + Results/Output */
const ReviewPresetLayout: React.FC = () => (
  <PanelGroup orientation="horizontal">
    <Panel defaultSize={45} minSize={25}>
      <DocumentPane />
    </Panel>
    <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />
    <Panel defaultSize={55} minSize={30}>
      <ResultsPane />
    </Panel>
  </PanelGroup>
);

/** Compare: not implemented yet — shown honestly rather than as a
 * functional-looking two-document picker that has no wiring behind it. */
const ComparePresetLayout: React.FC = () => (
  <div className="pane-container">
    <div className="pane-header">
      <div className="pane-header-title">
        <GitCompare size={14} />
        <span>Compare</span>
      </div>
    </div>
    <div className="pane-content">
      <EmptyState
        icon={GitCompare}
        title="Compare mode isn't available yet"
        description="Document comparison is planned but not implemented. Use Inspect or Review to work with one document at a time."
      />
    </div>
  </div>
);
