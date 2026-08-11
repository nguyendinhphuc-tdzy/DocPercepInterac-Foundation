import type { MappingProposal } from '../../types/chat';
import { MappingNode } from './MappingNode';

interface MappingVisualProps {
  proposal: MappingProposal;
}

/** Inline source→dest preview, attached to an assistant message that proposed a mapping. */
export function MappingVisual({ proposal }: MappingVisualProps) {
  return (
    <div className="mapping-visual">
      <MappingNode
        elementId="proposal-source"
        label={`Source: ${proposal.source.label}`}
        sub={proposal.source.sub}
      />
      <div className="mapping-line" />
      <MappingNode
        elementId="proposal-dest"
        label={`Dest: ${proposal.dest.label}`}
        sub={proposal.dest.sub}
      />
    </div>
  );
}
