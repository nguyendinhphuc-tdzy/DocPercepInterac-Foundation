import { create } from 'zustand';

// Canonical cross-pane SELECTION identity — holds a real `element_id`
// (backend-derived, content-stable — see perception/element_classifier.py),
// never a stringified array index. `hoveredElementId` (workspaceStore.ts)
// is the parallel canonical HOVER identity; both are `element_id`-keyed so
// Document/Elements panes and every renderer share one identity, never two
// independently-mutable ones (Foundation Document Perception & Renderer
// Contract Hardening phase).
interface SyncState {
  selectedElementId: string | null;
  setSelectedElementId: (id: string | null) => void;
}

export const useSyncStore = create<SyncState>((set) => ({
  selectedElementId: null,
  setSelectedElementId: (id) => set({ selectedElementId: id }),
}));
