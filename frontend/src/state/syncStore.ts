import { create } from 'zustand';

// THE authoritative interaction state: what the user has selected, and which
// document is active. One store, one truth.
//
// Before this, the composer's "Selected: …" chip was derived from
// `activeDoc.elements.find(...)` while the request carried a separate
// `selected_element_id`. Those two could disagree — and did: reloading a
// document's elements emptied the chip while the id lived on, and a selection
// made in one document was dropped by the backend whenever the workspace held
// several documents and none was "active". The chip and the request now read
// the same field, so a displayed selection is a sent selection.
//
// Transitions are explicit (SELECT / ADD / REMOVE / CLEAR / CHANGE_ACTIVE_DOCUMENT).
// Typing is not one of them: nothing in the composer may mutate selection.

export interface SelectedElement {
  document_id: string;
  element_id: string;
  element_type: string;
  display_label: string;
  /** Whatever Foundation already knows about where this lives — never invented. */
  location: Record<string, unknown>;
  selection_source: 'document_view' | 'elements_pane' | 'citation' | 'agent';
}

interface SyncState {
  /** Every current selection, in the order the user made them. */
  selection: SelectedElement[];
  /** The document the panes are showing, by server doc_id. */
  activeDocumentId: string | null;

  /** Canonical single-selection id, for renderers that highlight one element. */
  selectedElementId: string | null;

  /** SELECT — replaces the selection with exactly this element (or clears it). */
  setSelectedElement: (element: SelectedElement | null) => void;
  /** Back-compatible SELECT by id; resolves the full record from the workspace. */
  setSelectedElementId: (elementId: string | null, source?: SelectedElement['selection_source']) => void;
  /** ADD_SELECTION — multi-select; the schema and the wire format both allow N. */
  addSelectedElement: (element: SelectedElement) => void;
  /** REMOVE_SELECTION */
  removeSelectedElement: (elementId: string) => void;
  /** CLEAR_SELECTION — the Deselect action, and nothing else. */
  clearSelection: () => void;
  /** CHANGE_ACTIVE_DOCUMENT — drops selections that belong to other documents. */
  setActiveDocumentId: (documentId: string | null) => void;
}

export const useSyncStore = create<SyncState>((set, get) => ({
  selection: [],
  activeDocumentId: null,
  selectedElementId: null,

  setSelectedElement: (element) => set({
    selection: element ? [element] : [],
    selectedElementId: element ? element.element_id : null,
  }),

  setSelectedElementId: (elementId, source = 'document_view') => {
    if (!elementId) {
      set({ selection: [], selectedElementId: null });
      return;
    }
    const resolved = resolveElement(elementId, source);
    set({
      selection: resolved ? [resolved] : get().selection,
      selectedElementId: elementId,
    });
  },

  addSelectedElement: (element) => set((state) => (
    state.selection.some((s) => s.element_id === element.element_id)
      ? state
      : { selection: [...state.selection, element], selectedElementId: element.element_id }
  )),

  removeSelectedElement: (elementId) => set((state) => {
    const selection = state.selection.filter((s) => s.element_id !== elementId);
    return {
      selection,
      selectedElementId: selection.length ? selection[selection.length - 1].element_id : null,
    };
  }),

  clearSelection: () => set({ selection: [], selectedElementId: null }),

  setActiveDocumentId: (documentId) => set((state) => ({
    activeDocumentId: documentId,
    // A selection belongs to its document. Switching documents is an explicit
    // context change, so selections from elsewhere are dropped here — and only
    // here, never as a side effect of typing.
    selection: state.selection.filter((s) => s.document_id === documentId),
    selectedElementId: state.selection.find((s) => s.document_id === documentId)?.element_id ?? null,
  })),
}));

/** Where the resolver reads documents from. Registered by workspaceStore. */
type ProvidedElement = {
  element_id?: string;
  type?: string;
  name?: string;
  anchor?: unknown;
};

type DocumentProvider = () => ReadonlyArray<{
  docId: string | null;
  elements: ReadonlyArray<ProvidedElement> | null;
}>;

let documentProvider: DocumentProvider | null = null;

export function registerDocumentProvider(provider: DocumentProvider): void {
  documentProvider = provider;
}

/** Build the canonical record for an element id from the workspace's own data. */
function resolveElement(
  elementId: string,
  source: SelectedElement['selection_source'],
): SelectedElement | null {
  // The workspace registers itself here at module load, so the two stores stay
  // free of a circular import while sharing one identity resolution.
  const workspace = documentProvider?.();
  if (!workspace) return null;

  for (const doc of workspace) {
    const element = doc.elements?.find((e) => e.element_id === elementId);
    if (element?.element_id && doc.docId) {
      return {
        document_id: doc.docId,
        element_id: element.element_id,
        element_type: String(element.type ?? 'element'),
        display_label: element.name || String(element.type ?? 'element'),
        location: locationOf(element.anchor as unknown as Record<string, unknown>),
        selection_source: source,
      };
    }
  }
  return null;
}

/** Copy the anchor fields Foundation already carries. Nothing is fabricated. */
function locationOf(anchor: Record<string, unknown> | undefined): Record<string, unknown> {
  if (!anchor) return {};
  const keys = [
    'format', 'sheet_name', 'cell_address', 'from_cell', 'to_cell',
    'paragraph_index', 'table_index', 'row_index', 'col_index',
    'page_number', 'drawing_id', 'media_id', 'run_index',
  ];
  const location: Record<string, unknown> = {};
  for (const key of keys) {
    if (anchor[key] !== undefined && anchor[key] !== null) location[key] = anchor[key];
  }
  return location;
}
