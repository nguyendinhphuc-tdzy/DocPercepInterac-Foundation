import React from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { WorkspaceHeader } from './WorkspaceHeader';
import { FileRail } from './FileRail';
import { AgentPane } from '../agent/AgentPane';
import { ElementsPane } from '../elements/ElementsPane';
import { ResultsPane } from '../results/ResultsPane';
import { DocumentPane } from '../document/DocumentPane';
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

/** Agent + Document — Balanced 50/50 split so document viewer is always comfortably readable */
const AgentPresetLayout: React.FC = () => (
  <PanelGroup orientation="horizontal">
    <Panel defaultSize={50} minSize={30}>
      <AgentPane />
    </Panel>
    <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />
    <Panel defaultSize={50} minSize={40}>
      <DocumentPane />
    </Panel>
  </PanelGroup>
);

/** Inspect: Document + Elements Explorer */
const InspectPresetLayout: React.FC = () => (
  <PanelGroup orientation="horizontal">
    <Panel defaultSize={50} minSize={35}>
      <DocumentPane />
    </Panel>
    <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />
    <Panel defaultSize={50} minSize={35}>
      <ElementsPane />
    </Panel>
  </PanelGroup>
);

/** Review: Document + Results/Output */
const ReviewPresetLayout: React.FC = () => (
  <PanelGroup orientation="horizontal">
    <Panel defaultSize={45} minSize={30}>
      <DocumentPane />
    </Panel>
    <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />
    <Panel defaultSize={55} minSize={35}>
      <ResultsPane />
    </Panel>
  </PanelGroup>
);

/** Compare: Full-width Document Pane configured for comparison */
const ComparePresetLayout: React.FC = () => (
  <DocumentPane />
);
