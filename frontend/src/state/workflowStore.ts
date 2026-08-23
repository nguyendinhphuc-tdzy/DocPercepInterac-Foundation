import { create } from 'zustand';
import {
  assignDocumentToSlot,
  fetchWorkflowState,
  keepDocumentForReview,
  removeDocumentFromSlot,
  startWorkflowSession,
  WorkflowApiError,
  type SlotId,
  type WorkflowId,
  type WorkflowState,
} from '../api/workflow';
import { useWorkspaceStore } from './workspaceStore';

// Intake state for a workflow that asks for named ROLES rather than "some
// documents". The server owns every verdict here: this store uploads a file
// through the generic document layer, tells the server which slot the user put
// it in, and renders the state that comes back. It never decides for itself
// whether a file matches its slot.

interface WorkflowStoreState {
  state: WorkflowState | null;
  /** Slot currently uploading + profiling, so the panel can show it in place. */
  pendingSlot: SlotId | null;
  pendingFilename: string | null;
  error: string | null;
  busy: boolean;

  ensureSession: (workflow: WorkflowId) => Promise<WorkflowState | null>;
  addFileToSlot: (slotId: SlotId, file: File) => Promise<void>;
  removeFromSlot: (slotId: SlotId, docId: string) => Promise<void>;
  keepForReview: (slotId: SlotId, docId: string) => Promise<void>;
  refresh: () => Promise<void>;
  reset: () => void;
}

function messageOf(err: unknown, fallback: string): string {
  return err instanceof WorkflowApiError ? err.message : fallback;
}

export const useWorkflowStore = create<WorkflowStoreState>((set, get) => ({
  state: null,
  pendingSlot: null,
  pendingFilename: null,
  error: null,
  busy: false,

  // The workflow session is keyed by the workspace session, which only exists
  // once a document has been uploaded — so this runs after the first upload
  // rather than when the user clicks "Start Workflow".
  ensureSession: async (workflow) => {
    const sessionId = useWorkspaceStore.getState().sessionId;
    if (!sessionId) return null;

    const current = get().state;
    if (current && current.session_id === sessionId) return current;

    try {
      const state = await startWorkflowSession(sessionId, workflow);
      set({ state, error: null });
      return state;
    } catch (err) {
      set({ error: messageOf(err, 'Could not start the workflow intake.') });
      return null;
    }
  },

  addFileToSlot: async (slotId, file) => {
    const workflow = useWorkspaceStore.getState().activeWorkflow;
    if (!workflow) return;

    set({ pendingSlot: slotId, pendingFilename: file.name, busy: true, error: null });
    try {
      // Step 1 — the generic document layer: upload + perceive. Identical to a
      // non-workflow upload; no role is implied by it.
      const uploaded = await useWorkspaceStore.getState().addDocumentAndWait(file);
      if (!uploaded) {
        set({
          error: useWorkspaceStore.getState().intakeError
            ?? `"${file.name}" could not be perceived, so it was not added to a slot.`,
        });
        return;
      }

      // Step 2 — the workflow layer: attach the role and let the server decide
      // whether the file's content actually matches it.
      const session = await get().ensureSession(workflow);
      if (!session) return;

      const result = await assignDocumentToSlot(session.session_id, slotId, uploaded.docId);
      set({ state: result, error: null });
    } catch (err) {
      set({ error: messageOf(err, 'Could not add this file to the workflow.') });
    } finally {
      set({ pendingSlot: null, pendingFilename: null, busy: false });
    }
  },

  removeFromSlot: async (slotId, docId) => {
    const state = get().state;
    if (!state) return;
    set({ busy: true, error: null });
    try {
      const next = await removeDocumentFromSlot(state.session_id, slotId, docId);
      set({ state: next });
      // The document itself stays in the session; drop it from the workspace
      // list too so the panel and the file rail cannot disagree.
      const workspace = useWorkspaceStore.getState();
      const doc = workspace.documents.find((d) => d.docId === docId);
      if (doc) workspace.removeDocument(doc.clientId);
    } catch (err) {
      set({ error: messageOf(err, 'Could not remove this file.') });
    } finally {
      set({ busy: false });
    }
  },

  keepForReview: async (slotId, docId) => {
    const state = get().state;
    if (!state) return;
    set({ busy: true, error: null });
    try {
      const next = await keepDocumentForReview(state.session_id, slotId, docId);
      set({ state: next });
    } catch (err) {
      set({ error: messageOf(err, 'Could not record the review decision.') });
    } finally {
      set({ busy: false });
    }
  },

  refresh: async () => {
    const sessionId = useWorkspaceStore.getState().sessionId;
    if (!sessionId) return;
    try {
      set({ state: await fetchWorkflowState(sessionId) });
    } catch {
      // A session with no intake yet is not an error worth surfacing.
    }
  },

  reset: () => set({ state: null, pendingSlot: null, pendingFilename: null, error: null, busy: false }),
}));
