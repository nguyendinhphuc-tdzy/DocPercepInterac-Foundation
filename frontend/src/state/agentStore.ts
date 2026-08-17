import { create } from 'zustand';
import { sendAgentChat } from '../api/agent';
import { useWorkspaceStore } from './workspaceStore';

export type AgentStatus = 'idle' | 'preparing' | 'processing' | 'completed' | 'error';

export interface AgentMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  steps?: { label: string; status: 'done' | 'active' | 'pending' }[];
}

interface AgentState {
  messages: AgentMessage[];
  status: AgentStatus;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearMessages: () => void;
}

let messageCounter = 0;
function nextId(): string {
  return `msg-${++messageCounter}-${Date.now()}`;
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

    // Gather context from workspace store
    const ws = useWorkspaceStore.getState();
    const fileNames = [
      ...ws.targetFiles.map(f => f.name),
      ...ws.sourceFiles.map(f => f.name),
    ];

    try {
      set({ status: 'processing' });

      const response = await sendAgentChat({
        process_id: ws.processId,
        message: content.trim(),
        context: {
          file_names: fileNames,
          selected_element: null,
          element_count: ws.targetElements.length,
          mapped_count: ws.mapped.length,
          mapped_summary: ws.mapped.slice(0, 20).map(m => ({
            target_anchor: m.target_anchor,
            target_value: m.target_value,
            confidence: m.confidence,
          })),
        },
      });

      const assistantMsg: AgentMessage = {
        id: nextId(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString(),
        steps: response.steps,
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

  clearMessages: () => set({ messages: [], status: 'idle', error: null }),
}));
