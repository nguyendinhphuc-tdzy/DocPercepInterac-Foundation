import { create } from 'zustand';
import {
  sendAgentChat,
  executeAgentAction,
  rejectAgentAction,
  AgentApiError,
  DEFAULT_AGENT_MODEL,
  type AgentModelId,
  type AgentProviderId,
  type AgentStep,
  type Citation,
  type ProposedAction,
} from '../api/agent';
import { sendPilotEvent } from '../api/pilot';
import { useWorkspaceStore } from './workspaceStore';
import { useSyncStore } from './syncStore';

export type AgentStatus = 'idle' | 'preparing' | 'processing' | 'completed' | 'error';

export interface AgentMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  /** Which model produced (or was asked for) this message — per-message, never rewritten. */
  model?: AgentModelId;
  provider?: AgentProviderId;
  steps?: AgentStep[];
  citations?: Citation[];
  proposedActions?: ProposedAction[];
  runId?: string | null;
}

export interface ProviderErrorInfo {
  message: string;
  /**
   * The model that actually failed. Retry re-sends to exactly this model, even
   * if the selector has been changed since — retry never means "try a
   * different model".
   */
  failedModel: AgentModelId;
  errorType?: string;
  lastPrompt: string;
}

interface AgentState {
  messages: AgentMessage[];
  status: AgentStatus;
  error: string | null;
  providerError: ProviderErrorInfo | null;
  selectedModel: AgentModelId;
  setSelectedModel: (model: AgentModelId) => void;
  sendMessage: (content: string, overrideModel?: AgentModelId) => Promise<void>;
  retryFailedMessage: () => Promise<void>;
  switchModelAndRetry: (targetModel: AgentModelId) => Promise<void>;
  dismissProviderError: () => void;
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

export const useAgentStore = create<AgentState>((set, get) => ({
  messages: [],
  status: 'idle',
  error: null,
  providerError: null,
  selectedModel: DEFAULT_AGENT_MODEL,

  setSelectedModel: (model: AgentModelId) => {
    const prev = get().selectedModel;
    if (prev === model) return;
    set({ selectedModel: model });
    sendPilotEvent('agent.model.changed', {
      previous_model: prev,
      new_model: model,
    });
  },

  sendMessage: async (content: string, overrideModel?: AgentModelId) => {
    if (!content.trim()) return;

    // The model is captured here, once, for the life of this request. Changing
    // the selector while this request is in flight must not retarget it — the
    // new selection applies to the next request only.
    const modelToSend = overrideModel ?? get().selectedModel;

    // Check if the last message was already this exact user prompt (e.g. from retry)
    const existingMessages = get().messages;
    const lastMsg = existingMessages[existingMessages.length - 1];
    const isRetry = lastMsg && lastMsg.role === 'user' && lastMsg.content === content.trim();

    if (!isRetry) {
      const userMsg: AgentMessage = {
        id: nextId(),
        role: 'user',
        content: content.trim(),
        timestamp: new Date().toISOString(),
        model: modelToSend,
      };

      set((state) => ({
        messages: [...state.messages, userMsg],
        status: 'preparing',
        error: null,
        providerError: null,
      }));
    } else {
      set({
        status: 'preparing',
        error: null,
        providerError: null,
      });
    }

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
        model_id: modelToSend,
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
        model: response.model_id ?? modelToSend,
        provider: response.provider,
        steps: response.steps,
        citations: response.citations,
        proposedActions: response.proposed_actions,
        runId: response.run_id,
      };

      set((state) => ({
        messages: [...state.messages, assistantMsg],
        status: 'completed',
        error: null,
        providerError: null,
      }));
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'An unexpected error occurred.';
      const errorType = err instanceof AgentApiError ? err.errorType : 'unknown';

      // Safe Error State: no assistant bubble is created, and no other model is
      // tried. The user sees an explicit failure for the model they chose and
      // decides what to do next.
      set({
        status: 'error',
        error: errorMsg,
        providerError: {
          message: errorMsg,
          failedModel: modelToSend,
          errorType,
          lastPrompt: content.trim(),
        },
      });
    }
  },

  retryFailedMessage: async () => {
    const pe = get().providerError;
    if (!pe || !pe.lastPrompt) return;
    // Retry always means the SAME model that failed, passed explicitly so the
    // current selector value cannot change what gets retried.
    await get().sendMessage(pe.lastPrompt, pe.failedModel);
  },

  switchModelAndRetry: async (targetModel: AgentModelId) => {
    // Only reachable from an explicit user choice of a specific model in the
    // error card. Nothing calls this automatically on failure.
    const pe = get().providerError;
    get().setSelectedModel(targetModel);
    if (pe && pe.lastPrompt) {
      await get().sendMessage(pe.lastPrompt, targetModel);
    }
  },

  dismissProviderError: () => {
    set({
      providerError: null,
      error: null,
      status: 'idle',
    });
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
              d.docId === targetDoc.docId ? { ...d, elements: updatedElements } : d
            ),
          }));
        }

        // Update action status in the message
        set((state) => ({
          messages: state.messages.map((m) => {
            if (m.id !== messageId || !m.proposedActions) return m;
            return {
              ...m,
              proposedActions: m.proposedActions.map((a) =>
                a.action_id === actionId
                  ? { ...a, status: 'applied' as const }
                  : a
              ),
            };
          }),
        }));
      }
    } catch (err) {
      console.error('Failed to execute action:', err);
    }
  },

  rejectAction: async (messageId: string, actionId: string) => {
    const ws = useWorkspaceStore.getState();
    if (!ws.sessionId) return;

    try {
      await rejectAgentAction({
        session_id: ws.sessionId,
        action_id: actionId,
      });

      // Update action status in the message
      set((state) => ({
        messages: state.messages.map((m) => {
          if (m.id !== messageId || !m.proposedActions) return m;
          return {
            ...m,
            proposedActions: m.proposedActions.map((a) =>
              a.action_id === actionId
                ? { ...a, status: 'rejected' as const }
                : a
            ),
          };
        }),
      }));
    } catch (err) {
      console.error('Failed to reject action:', err);
    }
  },

  clearMessages: () => set({ messages: [], status: 'idle', error: null, providerError: null }),
}));
