import { create } from 'zustand';
import {
  uploadDocument, fetchDocumentElements, patchElement, runGptsMapping, ApiError,
} from '../api/client';
import { useSyncStore } from './syncStore';
import type {
  DocumentFormat, EditHistoryEntry, ElementRowData, GptsMappingResult, MappedEntry, MediaAsset,
} from '../types/element';

// Three concepts, kept strictly separate (mirrors api/routes/documents.py's
// own docstring):
//
//   Document = one uploaded/perceived artifact (`WorkspaceDocument`,
//              identified by `docId` once known — see below).
//   Session  = the workspace context that owns every document added so
//              far (`sessionId` — one per workspace, shared by all of
//              them, never one-per-file).
//   Task     = an explicit user-requested operation. Does not exist in
//              this slice at all until `runGptsMappingTask` is called —
//              `gptsMapping` is the ONLY task-shaped state in this store,
//              and nothing here ever sets it as a side effect of upload.
//
// Shape:
//
//   sessionId
//     |
//     +-- documents[0] (docId) -- status: ready      -- elements
//     +-- documents[1] (docId) -- status: perceiving
//     +-- documents[2] (docId) -- status: error
//     +-- ...
//
// Uploading/perceiving documents never assigns them a role and never
// implies a task should run — see addDocument() below and
// runGptsMappingTask() further down (the one and only place roles are
// ever assigned, always from an explicit call).

// Perception layer: what formats the Foundation can even parse. This is
// NOT a source/target distinction — every format here is treated
// identically at upload time. (Mirrors api/routes/documents.py's
// SUPPORTED_FORMATS.)
const SUPPORTED_FORMATS: DocumentFormat[] = ['docx', 'xlsx', 'pdf'];

// UI Spec §6 — a product/UX recommendation, not a backend limit.
const MAX_DOCUMENTS_PER_TASK = 10;

function formatOf(file: File): DocumentFormat | null {
  const ext = file.name.split('.').pop()?.toLowerCase();
  return (SUPPORTED_FORMATS as string[]).includes(ext ?? '') ? (ext as DocumentFormat) : null;
}

export type AppView = 'home' | 'workspace' | 'history' | 'settings';
export type WorkspacePreset = 'agent' | 'inspect' | 'review' | 'compare';

export interface TaskHistoryEntry {
  id: string;
  name: string;
  fileCount: number;
  elementCount: number;
  timestamp: string;
  status: 'done' | 'error';
}

// A single perceived (or perceiving) document. No role — nothing here
// says "source" or "target". `clientId` is the stable identity used by the
// UI before/independent of the server's `docId` (e.g. while a upload is
// still in flight); once perceive resolves, `docId` is the identity used
// for every server call (PATCH, elements fetch, download), per the
// invariant that identity must never be a filename/array-index/upload-order.
export interface WorkspaceDocument {
  clientId: string;
  file: File;
  format: DocumentFormat | null;
  status: 'perceiving' | 'ready' | 'error';
  docId: string | null;
  elementCount: number;
  elements: ElementRowData[] | null; // fetched lazily — see ensureElementsLoaded
  media: MediaAsset[]; // embedded-image manifest, arrives alongside elements — see ensureElementsLoaded
  error: string | null;
  // Whether a patched version exists on the server yet — from a manual
  // edit or (for a target doc) a completed GTPS mapping run. Gates whether
  // the download link is shown at all, so it never points at a 404.
  hasPatch: boolean;
}

// The one and only place role assignment + task execution happens for the
// GTPS application. This is a "task" (Context refinement #1) — distinct
// from `documents` (Perceive-only) and never created implicitly by upload.
interface GptsMappingState {
  status: 'idle' | 'running' | 'done' | 'error';
  sourceDocClientIds: string[];
  targetDocClientId: string | null;
  mapped: MappedEntry[];
  downloadUrl: string | null;
  error: string | null;
}

interface WorkspaceState {
  // ── Navigation ──
  currentView: AppView;
  setCurrentView: (view: AppView) => void;

  // ── Workspace layout ──
  workspacePreset: WorkspacePreset;
  setWorkspacePreset: (preset: WorkspacePreset) => void;

  // ── Task history (localStorage-backed) ──
  taskHistory: TaskHistoryEntry[];
  addTaskToHistory: (entry: TaskHistoryEntry) => void;

  // ── Session + documents (generic — Perceive only, no roles) ──
  sessionId: string | null;
  documents: WorkspaceDocument[];
  activeDocClientId: string | null;
  intakeError: string | null;
  addDocument: (file: File) => void;
  removeDocument: (clientId: string) => void;
  setActiveDocClientId: (clientId: string | null) => void;
  ensureElementsLoaded: (clientId: string) => Promise<void>;
  resetWorkspace: () => void;

  // ── GTPS application (explicit action only — see components/gpts/) ──
  gptsMapping: GptsMappingState;
  runGptsMappingTask: (sourceDocClientIds: string[], targetDocClientId: string) => Promise<void>;

  // ── Live editing (PATCH /api/documents/<session_id>/elements/<doc_id>) ──
  editError: string | null;
  editElement: (clientId: string, index: number, newValue: string) => Promise<void>;

  // ── Undo ──
  editHistory: EditHistoryEntry[];
  isUndoing: boolean;
  undoLastEdit: () => Promise<void>;

  // ── Cross-pane highlighting — keyed by `element_id` (see syncStore.ts's
  // parallel `selectedElementId`), never by array index. ──
  hoveredElementId: string | null;
  setHoveredElement: (elementId: string | null) => void;
}

function loadTaskHistory(): TaskHistoryEntry[] {
  try {
    const raw = localStorage.getItem('foundation_task_history');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveTaskHistory(history: TaskHistoryEntry[]) {
  try {
    localStorage.setItem('foundation_task_history', JSON.stringify(history.slice(0, 20)));
  } catch {
    // Ignore localStorage errors
  }
}

// Coordinates concurrent uploads within the same synchronous batch (e.g.
// selecting multiple files at once) so only ONE of them establishes the
// shared session — see addDocument(). Module-level by design: it is pure
// upload-sequencing plumbing, not UI state that any component reads.
let pendingSessionPromise: Promise<string> | null = null;

function applyUploadSummary(
  set: (fn: (state: WorkspaceState) => Partial<WorkspaceState>) => void,
  get: () => WorkspaceState,
  clientId: string,
  summary: { session_id: string; doc_id: string; status: 'ready' | 'error'; element_count: number; error: string | null },
) {
  set((state) => ({
    sessionId: state.sessionId ?? summary.session_id,
    documents: state.documents.map((d) => d.clientId === clientId
      ? { ...d, docId: summary.doc_id, status: summary.status, elementCount: summary.element_count, error: summary.error }
      : d),
    // First successfully-perceived document becomes active automatically
    // so panes have something to show without an extra click.
    activeDocClientId: state.activeDocClientId ?? (summary.status === 'ready' ? clientId : null),
  }));
  if (summary.status === 'ready' && get().activeDocClientId === clientId) {
    get().ensureElementsLoaded(clientId);
  }
}

function newClientId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `doc-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const idleGptsMapping: GptsMappingState = {
  status: 'idle',
  sourceDocClientIds: [],
  targetDocClientId: null,
  mapped: [],
  downloadUrl: null,
  error: null,
};

const initialWorkspaceState = {
  currentView: 'home' as AppView,
  workspacePreset: 'agent' as WorkspacePreset,
  taskHistory: loadTaskHistory(),
  sessionId: null as string | null,
  documents: [] as WorkspaceDocument[],
  activeDocClientId: null as string | null,
  intakeError: null as string | null,
  gptsMapping: idleGptsMapping,
  editError: null as string | null,
  editHistory: [] as EditHistoryEntry[],
  isUndoing: false,
  hoveredElementId: null as string | null,
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  ...initialWorkspaceState,

  // ── Navigation ──
  setCurrentView: (view) => set({ currentView: view }),
  setWorkspacePreset: (preset) => set({ workspacePreset: preset }),

  // ── Task history ──
  addTaskToHistory: (entry) => {
    const updated = [entry, ...get().taskHistory.filter(t => t.id !== entry.id)].slice(0, 20);
    set({ taskHistory: updated });
    saveTaskHistory(updated);
  },

  // ── Documents: upload establishes context only, then Perceive runs
  // automatically (extract + anchor + classify — no roles, no task) ──
  addDocument: (file) => {
    const format = formatOf(file);
    if (format === null) {
      set({
        intakeError: `"${file.name}" isn't a supported type — Foundation can perceive .docx, .xlsx, or .pdf.`,
      });
      return;
    }

    // A UX soft limit only — not an architectural constraint (the backend
    // accepts any number of documents per session). Generic: applies to
    // every document uniformly, no source/target distinction.
    if (get().documents.length >= MAX_DOCUMENTS_PER_TASK) {
      set({
        intakeError: `You've reached the recommended limit of ${MAX_DOCUMENTS_PER_TASK} files. Remove a document to add another.`,
      });
      return;
    }

    const clientId = newClientId();
    const doc: WorkspaceDocument = {
      clientId, file, format, status: 'perceiving', docId: null, elementCount: 0,
      elements: null, media: [], error: null, hasPatch: false,
    };
    set((state) => ({ documents: [...state.documents, doc], intakeError: null }));

    (async () => {
      try {
        // Several documents can be added in the same synchronous batch
        // (e.g. selecting multiple files at once) before any of their
        // uploads has resolved — so `get().sessionId` may still be null
        // for every one of them. Coordinate through `pendingSessionPromise`
        // so only the first upload in a batch establishes the session;
        // every other upload in the same batch waits for that session_id
        // and then joins it explicitly, instead of each one silently
        // minting its own separate session.
        let sessionId = get().sessionId;
        if (!sessionId) {
          if (!pendingSessionPromise) {
            pendingSessionPromise = uploadDocument(file, null).then((summary) => {
              applyUploadSummary(set, get, clientId, summary);
              return summary.session_id;
            });
            await pendingSessionPromise;
            pendingSessionPromise = null;
            return; // this document's own upload already applied above
          }
          sessionId = await pendingSessionPromise;
        }

        const summary = await uploadDocument(file, sessionId);
        applyUploadSummary(set, get, clientId, summary);
      } catch (err) {
        set((state) => ({
          documents: state.documents.map((d) => d.clientId === clientId
            ? { ...d, status: 'error', error: err instanceof ApiError ? err.message : 'Upload failed.' }
            : d),
        }));
      }
    })();
  },

  removeDocument: (clientId) => set((state) => ({
    documents: state.documents.filter((d) => d.clientId !== clientId),
    activeDocClientId: state.activeDocClientId === clientId ? null : state.activeDocClientId,
  })),

  setActiveDocClientId: (clientId) => {
    set({ activeDocClientId: clientId });
    if (clientId) get().ensureElementsLoaded(clientId);
    // element_id is globally unique (derived from full anchor content —
    // see perception/element_classifier.py), so this isn't strictly needed
    // for correctness anymore the way it was when selection was keyed by
    // per-document array index; kept anyway so switching documents doesn't
    // leave an unrelated element from the previous document highlighted.
    useSyncStore.getState().setSelectedElementId(null);
  },

  ensureElementsLoaded: async (clientId) => {
    const { sessionId, documents } = get();
    const doc = documents.find((d) => d.clientId === clientId);
    if (!doc || !sessionId || !doc.docId || doc.status !== 'ready' || doc.elements !== null) return;

    try {
      const result = await fetchDocumentElements(sessionId, doc.docId);
      set((state) => ({
        documents: state.documents.map((d) => d.clientId === clientId
          ? { ...d, elements: result.elements, media: result.media }
          : d),
      }));
    } catch (err) {
      set((state) => ({
        documents: state.documents.map((d) => d.clientId === clientId
          ? { ...d, error: err instanceof ApiError ? err.message : 'Failed to load elements.' }
          : d),
      }));
    }
  },

  resetWorkspace: () => set({
    ...initialWorkspaceState,
    currentView: get().currentView,
    taskHistory: get().taskHistory,
  }),

  // ── GTPS application: the only place that ever assigns source/target
  // roles, and only ever in response to an explicit call (see
  // components/gpts/GptsMappingAction.tsx) — never automatic. ──
  runGptsMappingTask: async (sourceDocClientIds, targetDocClientId) => {
    const { sessionId, documents } = get();
    const sourceDocs = sourceDocClientIds
      .map((id) => documents.find((d) => d.clientId === id))
      .filter((d): d is WorkspaceDocument => !!d && d.docId !== null);
    const targetDoc = documents.find((d) => d.clientId === targetDocClientId);
    if (!sessionId || sourceDocs.length === 0 || !targetDoc?.docId) return;

    set({
      gptsMapping: {
        ...idleGptsMapping,
        status: 'running',
        sourceDocClientIds,
        targetDocClientId,
      },
    });

    try {
      const result: GptsMappingResult = await runGptsMapping(
        sessionId,
        sourceDocs.map((d) => d.docId as string),
        targetDoc.docId,
      );
      set({
        gptsMapping: {
          status: 'done',
          sourceDocClientIds,
          targetDocClientId,
          mapped: result.mapped,
          downloadUrl: result.download_url,
          error: null,
        },
      });
      get().addTaskToHistory({
        id: sessionId,
        name: targetDoc.file.name,
        fileCount: sourceDocs.length + 1,
        elementCount: result.target_elements.length,
        timestamp: new Date().toISOString(),
        status: 'done',
      });
      // The GTPS run may have patched the target document's file on disk —
      // drop the cached elements so the next view re-fetches the current
      // (patched) content instead of the stale pre-mapping snapshot, and
      // mark it as having a patch so the download link becomes visible.
      if (result.download_url) {
        set((state) => ({
          documents: state.documents.map((d) => d.clientId === targetDocClientId
            ? { ...d, elements: null, hasPatch: true }
            : d),
        }));
      }
    } catch (err) {
      set((state) => ({
        gptsMapping: {
          ...state.gptsMapping,
          status: 'error',
          error: err instanceof ApiError ? err.message : 'GTPS mapping failed.',
        },
      }));
    }
  },

  // ── Live editing ──
  editElement: async (clientId, index, newValue) => {
    const { sessionId, documents } = get();
    const doc = documents.find((d) => d.clientId === clientId);
    if (!sessionId || !doc?.docId || !doc.elements) return;
    const element = doc.elements[index];
    if (!element || newValue === element.text) return;

    const previousElements = doc.elements;
    const previousValue = element.text;
    set((state) => ({
      documents: state.documents.map((d) => d.clientId === clientId
        ? { ...d, elements: d.elements!.map((el, i) => i === index ? { ...el, text: newValue, source: 'manual' } : el) }
        : d),
      editError: null,
    }));

    try {
      await patchElement(sessionId, doc.docId, element.anchor, newValue);
      set((state) => ({
        editHistory: [...state.editHistory, { docClientId: clientId, index, anchor: element.anchor, previousValue }],
        documents: state.documents.map((d) => d.clientId === clientId ? { ...d, hasPatch: true } : d),
      }));
    } catch (err) {
      set((state) => ({
        documents: state.documents.map((d) => d.clientId === clientId
          ? { ...d, elements: previousElements }
          : d),
        editError: err instanceof ApiError ? err.message : 'Failed to save edit.',
      }));
    }
  },

  // ── Undo ──
  undoLastEdit: async () => {
    const { editHistory, documents, sessionId, isUndoing } = get();
    if (editHistory.length === 0 || !sessionId || isUndoing) return;

    const last = editHistory[editHistory.length - 1];
    const doc = documents.find((d) => d.clientId === last.docClientId);
    if (!doc?.docId || !doc.elements) return;
    const element = doc.elements[last.index];
    if (!element) return;

    const valueBeforeUndo = element.text;
    set((state) => ({
      editHistory: editHistory.slice(0, -1),
      isUndoing: true,
      editError: null,
      documents: state.documents.map((d) => d.clientId === last.docClientId
        ? { ...d, elements: d.elements!.map((el, i) => i === last.index ? { ...el, text: last.previousValue, source: 'manual' } : el) }
        : d),
    }));

    try {
      await patchElement(sessionId, doc.docId, last.anchor, last.previousValue);
      set({ isUndoing: false });
    } catch (err) {
      set((state) => ({
        documents: state.documents.map((d) => d.clientId === last.docClientId
          ? { ...d, elements: d.elements!.map((el, i) => i === last.index ? { ...el, text: valueBeforeUndo } : el) }
          : d),
        editHistory: [...state.editHistory, last],
        editError: err instanceof ApiError ? err.message : 'Failed to undo edit.',
        isUndoing: false,
      }));
    }
  },

  // Guarded: a no-op when the id hasn't actually changed. Without this,
  // every hover-driven set() produces a new store snapshot (even for an
  // unchanged id) and re-renders every subscriber — including panes that
  // scroll-into-view in response, which can shift layout under a
  // stationary cursor, fire a new native mouseenter, and cascade into a
  // genuine render loop (seen with dense grids like the XLSX viewer under
  // simultaneously-mounted Document + Elements panes).
  setHoveredElement: (elementId) => {
    if (get().hoveredElementId === elementId) return;
    set({ hoveredElementId: elementId });
  },
}));
