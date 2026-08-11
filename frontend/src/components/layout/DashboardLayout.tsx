import { Group, Panel, Separator } from 'react-resizable-panels';
import { InputViewer } from '../input-viewer/InputViewer';
import { ElementIndexTable } from '../element-index/ElementIndexTable';
import { IntentMappingPane } from '../intent-mapping/IntentMappingPane';
import { OutputTracePane } from '../output-trace/OutputTracePane';

/** The 4-pane dashboard grid (v4 §7.1) — one screen, splitters, not tabs. */
export function DashboardLayout() {
  return (
    <Group orientation="vertical" className="app-body">
      <Panel defaultSize="60%" minSize="20%">
        <Group orientation="horizontal">
          <Panel defaultSize="50%" minSize="20%">
            <InputViewer />
          </Panel>
          <Separator className="resize-handle-h" />
          <Panel defaultSize="50%" minSize="20%">
            <ElementIndexTable />
          </Panel>
        </Group>
      </Panel>
      <Separator className="resize-handle-v" />
      <Panel defaultSize="40%" minSize="20%">
        <Group orientation="horizontal">
          <Panel defaultSize="50%" minSize="20%">
            <IntentMappingPane />
          </Panel>
          <Separator className="resize-handle-h" />
          <Panel defaultSize="50%" minSize="20%">
            <OutputTracePane />
          </Panel>
        </Group>
      </Panel>
    </Group>
  );
}
