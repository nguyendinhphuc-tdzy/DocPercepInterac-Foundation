import React from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { WorkspaceHeader } from './WorkspaceHeader';
import { DocumentPane } from '../document/DocumentPane';
import { ElementsPane } from '../elements/ElementsPane';
import { AgentPane } from '../agent/AgentPane';
import { ResultsPane } from '../results/ResultsPane';

export const WorkspaceLayout: React.FC = () => {
  return (
    <div className="flex flex-col h-screen bg-white text-gray-900 font-sans">
      <WorkspaceHeader />
      
      <div className="flex-1 overflow-hidden">
        <PanelGroup orientation="vertical">
          {/* Top Half: Document and Elements */}
          <Panel defaultSize={55} minSize={30}>
            <PanelGroup orientation="horizontal">
              <Panel defaultSize={50} minSize={30}>
                <DocumentPane />
              </Panel>
              <ResizeHandle />
              <Panel defaultSize={50} minSize={30}>
                <ElementsPane />
              </Panel>
            </PanelGroup>
          </Panel>

          <ResizeHandle horizontal />

          {/* Bottom Half: Agent and Results */}
          <Panel defaultSize={45} minSize={20}>
            <PanelGroup orientation="horizontal">
              <Panel defaultSize={50} minSize={30}>
                <AgentPane />
              </Panel>
              <ResizeHandle />
              <Panel defaultSize={50} minSize={30}>
                <ResultsPane />
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </div>
    </div>
  );
};

// Custom Resize Handle
const ResizeHandle = ({ horizontal = false }: { horizontal?: boolean }) => {
  return (
    <PanelResizeHandle className={`
      relative bg-gray-200 transition-colors hover:bg-blue-400
      ${horizontal ? 'h-[1px] hover:h-[3px] w-full cursor-row-resize' : 'w-[1px] hover:w-[3px] h-full cursor-col-resize'}
    `} />
  );
};
