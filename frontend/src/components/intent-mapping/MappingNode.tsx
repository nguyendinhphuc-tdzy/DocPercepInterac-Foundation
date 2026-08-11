interface MappingNodeProps {
  label: string;
  sub: string;
  elementId?: string;
}

export function MappingNode({ label, sub, elementId }: MappingNodeProps) {
  return (
    <div className={`mapping-node${elementId ? ' sync-target' : ''}`}>
      {label}
      <br />
      <span className="mapping-node-sub">{sub}</span>
    </div>
  );
}
