import React, { useEffect } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { WorkspaceHeader } from './WorkspaceHeader';
import { FileRail } from './FileRail';
import { AgentPane } from '../agent/AgentPane';
import { ElementsPane } from '../elements/ElementsPane';
import { ResultsPane } from '../results/ResultsPane';
import { DocumentPane } from '../document/DocumentPane';
import { useWorkspaceStore } from '../../state/workspaceStore';

export const WorkspaceView: React.FC = () => {
  const { workspacePreset, setCurrentView } = useWorkspaceStore();

  // If no documents have been added, redirect to new-task.
  useEffect(() => {
    const { documents } = useWorkspaceStore.getState();
    if (documents.length === 0) {
      setCurrentView('new-task');
    }
  }, [setCurrentView]);

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

/** Compare: Source A + Source B (placeholder) */
const ComparePresetLayout: React.FC = () => (
  <PanelGroup orientation="horizontal">
    <Panel defaultSize={50} minSize={30}>
      <div className="empty-state">
        <div className="empty-title">Source A</div>
        <div className="empty-description">Select a document to compare.</div>
      </div>
    </Panel>
    <PanelResizeHandle className="resize-handle" data-orientation="horizontal" />
    <Panel defaultSize={50} minSize={30}>
      <div className="empty-state">
        <div className="empty-title">Source B</div>
        <div className="empty-description">Select a document to compare.</div>
      </div>
    </Panel>
  </PanelGroup>
);
