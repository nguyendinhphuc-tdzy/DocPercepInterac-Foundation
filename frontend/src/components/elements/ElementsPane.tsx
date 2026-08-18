import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Layers, Search, ChevronRight, ChevronDown, Eye, Loader2 } from 'lucide-react';
import { useWorkspaceStore } from '../../state/workspaceStore';
import { useSyncStore } from '../../state/syncStore';
import { ConfidenceBadge } from '../shared/ConfidenceBadge';
import { EmptyState } from '../shared/EmptyState';
import type { ElementRowData } from '../../types/element';

interface ElementGroup {
  label: string;
  type: 'section' | 'table' | 'sheet' | 'page';
  elements: ElementRowData[];
}

// A stable reference for "no elements yet" (e.g. a document mid-fetch,
// where `elements` is `null`). `?? []` alone would allocate a NEW empty
// array on every render, making any useMemo/useEffect keyed on that value
// recompute every render too — which previously cascaded into a genuine
// infinite render loop (groups -> setExpandedGroups -> re-render -> new
// `[]` -> new groups -> ...) for any document still loading its elements.
const EMPTY_ELEMENTS: ElementRowData[] = [];

// Semantic grouping, format-aware: DOCX groups by heading section + table
// (structural, matches how the document actually reads); XLSX groups by
// sheet; PDF groups by page. Every format gets SOME real grouping instead
// of one giant flat "Document" bucket — this is what keeps the Element
// Explorer a genuine "trust & verification layer" (spec §17-19) rather
// than a raw table dump, regardless of source format.
function groupElements(elements: ElementRowData[]): ElementGroup[] {
  const groups: ElementGroup[] = [];
  let currentSection: ElementGroup | null = null;

  const closeCurrentSection = () => {
    if (currentSection && currentSection.elements.length > 0) groups.push(currentSection);
    currentSection = null;
  };

  const pushOrAppend = (label: string, type: ElementGroup['type'], el: ElementRowData) => {
    const existing = groups.find((g) => g.label === label && g.type === type);
    if (existing) {
      existing.elements.push(el);
    } else {
      closeCurrentSection();
      groups.push({ label, type, elements: [el] });
    }
  };

  for (const el of elements) {
    if (el.anchor.format === 'xlsx') {
      pushOrAppend(el.anchor.sheet_name, 'sheet', el);
      continue;
    }

    if (el.anchor.format === 'pdf') {
      pushOrAppend(`Page ${el.anchor.page}`, 'page', el);
      continue;
    }

    // DOCX: heading-delimited sections, with tables grouped by table_index
    // (1-indexed for display — table_index itself is 0-indexed internally).
    if (el.type === 'heading') {
      closeCurrentSection();
      currentSection = { label: el.text || `Section ${el.index}`, type: 'section', elements: [el] };
    } else if (el.type === 'cell' && el.anchor.table_index !== null && el.anchor.table_index !== undefined) {
      pushOrAppend(`Table ${el.anchor.table_index + 1}`, 'table', el);
    } else {
      if (!currentSection) {
        currentSection = { label: 'Document', type: 'section', elements: [] };
      }
      currentSection.elements.push(el);
    }
  }

  closeCurrentSection();

  // If no groups were created, make one flat group
  if (groups.length === 0 && elements.length > 0) {
    groups.push({ label: 'All Elements', type: 'section', elements });
  }

  return groups;
}

export const ElementsPane: React.FC = () => {
  const { documents, activeDocClientId, hoveredElementIndex, setHoveredElement } = useWorkspaceStore();
  const activeDoc = documents.find((d) => d.clientId === activeDocClientId) ?? null;
  const activeElements = activeDoc?.elements ?? EMPTY_ELEMENTS;
  const { activeElementId, setActive } = useSyncStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const itemRefs = useRef(new Map<number, HTMLButtonElement>());

  // Auto-expand all groups initially
  const groups = useMemo(() => groupElements(activeElements), [activeElements]);

  useEffect(() => {
    setExpandedGroups(new Set(groups.map(g => g.label)));
  }, [groups]);

  // Scroll to hovered element
  useEffect(() => {
    if (hoveredElementIndex != null) {
      itemRefs.current.get(hoveredElementIndex)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [hoveredElementIndex]);

  // Reverse cross-pane sync: clicking an element in the Document viewer
  // selects it here too (same syncStore, same element index) — reveal it
  // even if its group wasn't already scrolled into view.
  useEffect(() => {
    if (!activeElementId) return;
    const idx = parseInt(activeElementId);
    if (!isNaN(idx)) {
      itemRefs.current.get(idx)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [activeElementId]);

  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return groups;
    const q = searchQuery.toLowerCase();
    return groups
      .map(g => ({
        ...g,
        elements: g.elements.filter(el =>
          el.text.toLowerCase().includes(q) ||
          el.type.toLowerCase().includes(q) ||
          el.name.toLowerCase().includes(q)
        ),
      }))
      .filter(g => g.elements.length > 0);
  }, [groups, searchQuery]);

  const toggleGroup = (label: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const selectedIndex = activeElementId ? parseInt(activeElementId) : null;

  return (
    <div className="pane-container">
      <div className="pane-header">
        <div className="pane-header-title">
          <Layers size={14} />
          <span>Elements</span>
        </div>
        <div className="pane-header-actions">
          <span style={{ fontSize: 'var(--text-xxs)', color: 'var(--text-tertiary)' }}>
            {activeElements.length.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Search */}
      {activeElements.length > 0 && (
        <div style={{
          padding: 'var(--space-2) var(--space-3)',
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--space-2)',
            background: 'var(--bg-app)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-md)',
            padding: '0 var(--space-2)',
          }}>
            <Search size={13} style={{ color: 'var(--text-tertiary)', flexShrink: 0 }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search elements..."
              style={{
                flex: 1,
                border: 'none',
                background: 'transparent',
                fontSize: 'var(--text-sm)',
                padding: 'var(--space-2) 0',
                outline: 'none',
                color: 'var(--text-primary)',
                fontFamily: 'inherit',
              }}
              aria-label="Search elements"
            />
          </div>
        </div>
      )}

      {/* Content */}
      <div className="pane-content">
        {activeElements.length === 0 ? (
          <EmptyState
            icon={activeDoc?.status === 'perceiving' || (!!activeDoc && activeDoc.elements === null) ? Loader2 : Layers}
            iconClassName={activeDoc?.status === 'perceiving' || (!!activeDoc && activeDoc.elements === null) ? 'animate-spin' : undefined}
            title={
              activeDoc?.status === 'perceiving'
                ? 'Reading document…'
                : activeDoc && activeDoc.elements === null
                  ? 'Loading elements…'
                  : 'No elements extracted'
            }
            description={
              activeDoc ? '' : 'Add a document to see its extracted elements.'
            }
          />
        ) : (
          <div className="element-tree">
            {filteredGroups.map((group) => {
              const isExpanded = expandedGroups.has(group.label);
              return (
                <div key={group.label} className="element-tree-group">
                  <button
                    className="element-tree-group-header"
                    onClick={() => toggleGroup(group.label)}
                    aria-expanded={isExpanded}
                  >
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <span>{group.label}</span>
                    <span style={{
                      marginLeft: 'auto',
                      fontSize: 'var(--text-xxs)',
                      color: 'var(--text-tertiary)',
                    }}>
                      {group.elements.length}
                    </span>
                  </button>

                  {isExpanded && group.elements.map((el) => {
                    const isSelected = selectedIndex === el.index;
                    const isHighlighted = hoveredElementIndex === el.index;
                    return (
                      <button
                        key={el.index}
                        ref={(node) => {
                          if (node) itemRefs.current.set(el.index, node);
                          else itemRefs.current.delete(el.index);
                        }}
                        className={`element-tree-item ${isSelected ? 'selected' : ''} ${isHighlighted ? 'highlighted' : ''}`}
                        onClick={() => setActive(String(el.index))}
                        onMouseEnter={() => setHoveredElement(el.index)}
                        onMouseLeave={() => setHoveredElement(null)}
                        aria-selected={isSelected}
                      >
                        <span className="element-text" title={el.text}>
                          {el.text || '(empty)'}
                        </span>
                        <span className="element-type">{el.type}</span>
                        {/* Deterministic perception is uniformly 100% confident — showing
                            that identical number next to every single row is the exact
                            "visual noise" UI Spec §25 warns against. Only surface the
                            badge here when it's actually informative (i.e. not full
                            confidence); the exact value always remains visible in the
                            Inspector below for any selected element. */}
                        {el.confidence != null && el.confidence < 0.999 && (
                          <ConfidenceBadge confidence={el.confidence} />
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Inspector (inline when element selected) */}
      {selectedIndex != null && activeElements[selectedIndex] && (
        <ElementInspectorInline element={activeElements[selectedIndex]} />
      )}
    </div>
  );
};

// ── Inline Inspector ── //
const ElementInspectorInline: React.FC<{ element: ElementRowData }> = ({ element }) => {
  const { setHoveredElement } = useWorkspaceStore();

  const anchorDisplay = (() => {
    const a = element.anchor;
    if (a.format === 'docx') {
      if ('table_index' in a && a.table_index != null) {
        return `Table ${a.table_index} · Row ${a.row_index ?? '?'} · Col ${a.col_index ?? '?'}`;
      }
      if ('paragraph_index' in a) return `Paragraph ${a.paragraph_index}`;
      return a.style_id || 'DOCX element';
    }
    if (a.format === 'xlsx') return `${a.sheet_name}!${a.cell_address}`;
    if (a.format === 'pdf') return `Page ${a.page} · Region ${a.reading_order_index}`;
    return 'Unknown';
  })();

  return (
    <div style={{
      borderTop: '1px solid var(--border)',
      background: 'var(--bg-surface-secondary)',
      maxHeight: 220,
      overflow: 'auto',
    }}>
      <div className="inspector">
        <div className="inspector-field">
          <div className="inspector-field-label">Type</div>
          <div className="inspector-field-value" style={{ textTransform: 'capitalize' }}>{element.type}</div>
        </div>
        <div className="inspector-field">
          <div className="inspector-field-label">Content</div>
          <div className="inspector-field-value">{element.text || '(empty)'}</div>
        </div>
        <div className="inspector-field">
          <div className="inspector-field-label">Position</div>
          <div className="inspector-field-value mono">{anchorDisplay}</div>
        </div>
        {element.confidence != null && (
          <div className="inspector-field">
            <div className="inspector-field-label">Confidence</div>
            <div className="inspector-field-value">
              <ConfidenceBadge confidence={element.confidence} />
            </div>
          </div>
        )}
        {element.source && (
          <div className="inspector-field">
            <div className="inspector-field-label">Source</div>
            <div className="inspector-field-value" style={{ textTransform: 'capitalize' }}>
              {element.source === 'manual' ? 'Manually edited' : element.source.replace('_', ' ')}
            </div>
          </div>
        )}
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setHoveredElement(element.index)}
          style={{ alignSelf: 'flex-start' }}
        >
          <Eye size={13} />
          <span>Reveal in document</span>
        </button>
      </div>
    </div>
  );
};
