import { create } from 'zustand';
import {
  sendAgentChat,
  executeAgentAction,
  rejectAgentAction,
  type AgentStep,
  type Citation,
  type ProposedAction,
} from '../api/agent';
import { useWorkspaceStore } from './workspaceStore';
import { useSyncStore } from './syncStore';

export type AgentStatus = 'idle' | 'preparing' | 'processing' | 'completed' | 'error';

export interface AgentMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  steps?: AgentStep[];
  citations?: Citation[];
  proposedActions?: ProposedAction[];
  runId?: string | null;
}

interface AgentState {
  messages: AgentMessage[];
  status: AgentStatus;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  confirmAction: (messageId: string, actionId: string) => Promise<void>;
  rejectAction: (messageId: string, actionId: string) => Promise<void>;
  clearMessages: () => void;
}

function nextId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export const useAgentStore = create<AgentState>((set) => ({
  messages: [],
  status: 'idle',
  error: null,

  sendMessage: async (content: string) => {
    if (!content.trim()) return;

    const userMsg: AgentMessage = {
      id: nextId(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMsg],
      status: 'preparing',
      error: null,
    }));

    const ws = useWorkspaceStore.getState();
    const sync = useSyncStore.getState();
    const activeDoc = ws.documents.find((d) => d.clientId === ws.activeDocClientId);
    const fileNames = ws.documents.map((d) => d.file.name);
    const totalElementCount = ws.documents.reduce((sum, d) => sum + d.elementCount, 0);

    try {
      set({ status: 'processing' });

      const response = await sendAgentChat({
        session_id: ws.sessionId,
        message: content.trim(),
        context: {
          active_doc_id: activeDoc?.docId ?? null,
          selected_element_id: sync.selectedElementId,
          file_names: fileNames,
          element_count: totalElementCount,
        },
      });

      const assistantMsg: AgentMessage = {
        id: nextId(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        steps: response.steps,
        citations: response.citations,
        proposedActions: response.proposed_actions,
        runId: response.run_id,
      };

      set((state) => ({
        messages: [...state.messages, assistantMsg],
        status: 'completed',
      }));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An unexpected error occurred.';

      const errorAssistantMsg: AgentMessage = {
        id: nextId(),
        role: 'assistant',
        content: `Error: ${errorMsg}`,
        timestamp: new Date().toISOString(),
      };

      set((state) => ({
        messages: [...state.messages, errorAssistantMsg],
        status: 'error',
        error: errorMsg,
      }));
    }
  },

  confirmAction: async (messageId: string, actionId: string) => {
    const ws = useWorkspaceStore.getState();
    if (!ws.sessionId) return;

    try {
      const result = await executeAgentAction({
        session_id: ws.sessionId,
        action_id: actionId,
      });

      if (result.status === 'success') {
        // Refresh active document from Foundation backend
        const targetDoc = ws.documents.find((d) => d.docId === result.doc_id);
        if (targetDoc && targetDoc.elements) {
          const updatedElements = targetDoc.elements.map((el) => {
            if (el.element_id === result.element_id) {
              return { ...el, text: result.new_value, value: result.new_value };
            }
            return el;
          });
          useWorkspaceStore.setState((s) => ({
            documents: s.documents.map((d) =>
              d.clientId === targetDoc.clientId
                ? { ...d, elements: updatedElements, hasPatch: true }
                : d
            ),
          }));
        }

        // Mark action as applied in message state
        set((state) => ({
          messages: state.messages.map((m) =>
            m.id === messageId && m.proposedActions
              ? {
                  ...m,
                  proposedActions: m.proposedActions.map((a) =>
                    a.action_id === actionId ? { ...a, status: 'applied' } : a
                  ),
                }
              : m
          ),
        }));
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Action execution failed.';
      alert(`Could not execute action: ${errorMsg}`);
    }
  },

  rejectAction: async (messageId: string, actionId: string) => {
    const ws = useWorkspaceStore.getState();
    if (ws.sessionId) {
      try {
        await rejectAgentAction({
          session_id: ws.sessionId,
          action_id: actionId,
        });
      } catch (err) {
        console.error('Failed to persist action rejection on server:', err);
      }
    }

    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId && m.proposedActions
          ? {
              ...m,
              proposedActions: m.proposedActions.map((a) =>
                a.action_id === actionId ? { ...a, status: 'rejected' } : a
              ),
            }
          : m
      ),
    }));
  },

  clearMessages: () => set({ messages: [], status: 'idle', error: null }),
}));

