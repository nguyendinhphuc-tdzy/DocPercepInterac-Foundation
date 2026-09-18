/**
 * GTPS Real-Document Demo — Zustand store.
 * =========================================
 * Location: frontend/src/state/gtpsDemoStore.ts
 *
 * Manages demo session lifecycle: file intake → role assignment →
 * analysis → review projection → document preview switching.
 *
 * Completely isolated from the production workspaceStore — different
 * session model, different endpoints, different lifecycle.
 */
import { create } from 'zustand';
import {
  createDemoWorkspace,
  assignDemoRole,
  removeDemoDoc,
  runDemoAnalysis,
  recordDemoDecision,
  demoDocContentUrl,
  fetchDemoDocElements,
  type DemoDocInfo,
  type DemoReadiness,
  type ReviewProjection,
} from '../api/demo';

// ── Types ──

export type DemoStage = 'intake' | 'analyzing' | 'review';
export type DemoViewMode = 'dual-comparison' | 'preview-template' | 'preview-historical' | 'preview-source';
export type StatusFilter = 'ALL' | 'MAPPED' | 'NEEDS_CONFIRMATION' | 'MISSING_SOURCE' | 'UNSUPPORTED';

interface GtpsDemoState {
  // Session
  sessionId: string | null;
  documents: DemoDocInfo[];
  roles: {
    TARGET_TEMPLATE: string | null;
    HISTORICAL_REFERENCE: string | null;
    CURRENT_SOURCE: string[];
  };
  readiness: DemoReadiness;

  // Stage management
  stage: DemoStage;
  analyzeError: string | null;
  analyzeProgress: string | null;

  // Review projection (from /analyze)
  reviewProjection: ReviewProjection | null;

  // View state
  viewMode: DemoViewMode;
  selectedProposalId: string | null;
  hoveredProposalId: string | null;
  statusFilter: StatusFilter;
  previewDocId: string | null;  // which doc is currently previewed in single-doc mode

  // Document bytes cache (ArrayBuffer keyed by doc_id)
  docBytesCache: Map<string, ArrayBuffer>;
  docElementsCache: Map<string, any[]>;

  // Actions
  loadLocalDemo: () => Promise<void>;
  uploadFiles: (files: File[]) => Promise<void>;
  assignRole: (docId: string, role: string | null) => Promise<void>;
  removeDocument: (docId: string) => Promise<void>;
  runAnalysis: () => Promise<void>;
  setSelectedProposal: (id: string | null) => void;
  setHoveredProposal: (id: string | null) => void;
  setStatusFilter: (filter: StatusFilter) => void;
  setViewMode: (mode: DemoViewMode) => void;
  previewDocument: (docId: string) => void;
  returnToComparison: () => void;
  recordDecision: (proposalId: string, decision: string, notes?: string) => Promise<void>;
  fetchDocBytes: (docId: string) => Promise<ArrayBuffer>;
  fetchDocElements: (docId: string) => Promise<any[]>;
  reset: () => void;
}

const emptyReadiness: DemoReadiness = {
  template_ready: false,
  historical_ready: false,
  current_source_ready: false,
  all_ready: false,
};

const emptyRoles = {
  TARGET_TEMPLATE: null as string | null,
  HISTORICAL_REFERENCE: null as string | null,
  CURRENT_SOURCE: [] as string[],
};

const initialState = {
  sessionId: null as string | null,
  documents: [] as DemoDocInfo[],
  roles: { ...emptyRoles },
  readiness: { ...emptyReadiness },
  stage: 'intake' as DemoStage,
  analyzeError: null as string | null,
  analyzeProgress: null as string | null,
  reviewProjection: null as ReviewProjection | null,
  viewMode: 'dual-comparison' as DemoViewMode,
  selectedProposalId: null as string | null,
  hoveredProposalId: null as string | null,
  statusFilter: 'ALL' as StatusFilter,
  previewDocId: null as string | null,
  docBytesCache: new Map<string, ArrayBuffer>(),
  docElementsCache: new Map<string, any[]>(),
};

export const useGtpsDemoStore = create<GtpsDemoState>((set, get) => ({
  ...initialState,

  loadLocalDemo: async () => {
    try {
      set({ analyzeProgress: 'Đang nạp tệp mẫu thực tế…', analyzeError: null });
      const result = await createDemoWorkspace({ loadLocalDemo: true });
      set({
        sessionId: result.session_id,
        documents: result.documents,
        roles: result.roles,
        readiness: result.readiness,
        analyzeProgress: null,
      });
    } catch (err) {
      set({ analyzeError: err instanceof Error ? err.message : 'Failed to load demo files.', analyzeProgress: null });
    }
  },

  uploadFiles: async (files: File[]) => {
    try {
      set({ analyzeError: null, analyzeProgress: 'Đang tải lên…' });
      const result = await createDemoWorkspace({
        sessionId: get().sessionId ?? undefined,
        files,
      });
      set({
        sessionId: result.session_id,
        documents: result.documents,
        roles: result.roles,
        readiness: result.readiness,
        analyzeProgress: null,
      });
    } catch (err) {
      set({ analyzeError: err instanceof Error ? err.message : 'Upload failed.', analyzeProgress: null });
    }
  },

  assignRole: async (docId, role) => {
    const { sessionId } = get();
    if (!sessionId) return;
    try {
      const result = await assignDemoRole(sessionId, docId, role);
      set({
        documents: result.documents,
        roles: result.roles,
        readiness: result.readiness,
        reviewProjection: null,
      });
    } catch (err) {
      set({ analyzeError: err instanceof Error ? err.message : 'Role assignment failed.' });
    }
  },

  removeDocument: async (docId) => {
    const { sessionId } = get();
    if (!sessionId) return;
    try {
      const result = await removeDemoDoc(sessionId, docId);
      set({
        documents: result.documents,
        roles: result.roles,
        readiness: result.readiness,
        reviewProjection: null,
      });
    } catch (err) {
      set({ analyzeError: err instanceof Error ? err.message : 'Remove failed.' });
    }
  },

  runAnalysis: async () => {
    const { sessionId } = get();
    if (!sessionId) return;
    try {
      set({ stage: 'analyzing', analyzeError: null, analyzeProgress: 'Đang phân tích ánh xạ…' });
      const projection = await runDemoAnalysis(sessionId);
      set({
        stage: 'review',
        reviewProjection: projection,
        analyzeProgress: null,
        viewMode: 'dual-comparison',
        selectedProposalId: null,
        statusFilter: 'ALL',
      });
    } catch (err) {
      set({
        stage: 'intake',
        analyzeError: err instanceof Error ? err.message : 'Analysis failed.',
        analyzeProgress: null,
      });
    }
  },

  setSelectedProposal: (id) => set({ selectedProposalId: id }),
  setHoveredProposal: (id) => {
    if (get().hoveredProposalId === id) return;
    set({ hoveredProposalId: id });
  },
  setStatusFilter: (filter) => set({ statusFilter: filter }),
  setViewMode: (mode) => set({ viewMode: mode }),

  previewDocument: (docId) => {
    const doc = get().documents.find(d => d.doc_id === docId);
    if (!doc) return;
    const role = doc.assigned_role;
    let mode: DemoViewMode = 'preview-source';
    if (role === 'TARGET_TEMPLATE') mode = 'preview-template';
    else if (role === 'HISTORICAL_REFERENCE') mode = 'preview-historical';
    set({ viewMode: mode, previewDocId: docId });
  },

  returnToComparison: () => set({ viewMode: 'dual-comparison', previewDocId: null }),

  recordDecision: async (proposalId, decision, notes) => {
    const { sessionId, reviewProjection } = get();
    if (!sessionId || !reviewProjection) return;
    try {
      await recordDemoDecision(sessionId, proposalId, decision, notes);
      // Update local projection
      const updatedProposals = reviewProjection.proposals.map(p =>
        p.id === proposalId ? { ...p, decision } : p
      );
      set({
        reviewProjection: {
          ...reviewProjection,
          proposals: updatedProposals,
        },
      });
    } catch (err) {
      set({ analyzeError: err instanceof Error ? err.message : 'Decision recording failed.' });
    }
  },

  fetchDocBytes: async (docId: string) => {
    const cached = get().docBytesCache.get(docId);
    if (cached) return cached;
    const url = demoDocContentUrl(docId);
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch doc ${docId}`);
    const buf = await res.arrayBuffer();
    set(state => {
      const next = new Map(state.docBytesCache);
      next.set(docId, buf);
      return { docBytesCache: next };
    });
    return buf;
  },

  fetchDocElements: async (docId: string) => {
    const cached = get().docElementsCache.get(docId);
    if (cached) return cached;
    const result = await fetchDemoDocElements(docId);
    set(state => {
      const next = new Map(state.docElementsCache);
      next.set(docId, result.elements);
      return { docElementsCache: next };
    });
    return result.elements;
  },

  reset: () => set({
    ...initialState,
    docBytesCache: new Map(),
    docElementsCache: new Map(),
  }),
}));
