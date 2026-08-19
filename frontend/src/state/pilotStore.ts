import { create } from 'zustand';
import { sendPilotEvent, fetchPilotScenarios, type PilotScenario } from '../api/pilot';

function newId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `pilot-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

interface PilotState {
  pilotSessionId: string;
  pilotModeEnabled: boolean;
  scenarios: PilotScenario[];
  activeScenarioId: string | null;
  taskId: string | null;
  taskStartedAt: string | null;
  togglePilotMode: () => void;
  loadScenarios: () => Promise<void>;
  startTask: (scenarioId: string) => void;
  completeTask: () => void;
  abandonTask: () => void;
}

// One pilot_session_id per browser tab load — correlates every event this
// tab emits without requiring a new account/session model (see phase scope).
const PILOT_SESSION_ID = newId();

export const usePilotStore = create<PilotState>((set, get) => {
  // Fired once, at module load, not inside a render path.
  sendPilotEvent('pilot.session.started', { pilot_session_id: PILOT_SESSION_ID });

  return {
    pilotSessionId: PILOT_SESSION_ID,
    pilotModeEnabled: false,
    scenarios: [],
    activeScenarioId: null,
    taskId: null,
    taskStartedAt: null,

    togglePilotMode: () => {
      const enabling = !get().pilotModeEnabled;
      set({ pilotModeEnabled: enabling });
      if (enabling && get().scenarios.length === 0) {
        void get().loadScenarios();
      }
    },

    loadScenarios: async () => {
      const scenarios = await fetchPilotScenarios();
      set({ scenarios });
    },

    startTask: (scenarioId: string) => {
      const taskId = newId();
      const startedAt = new Date().toISOString();
      set({ activeScenarioId: scenarioId, taskId, taskStartedAt: startedAt });
      sendPilotEvent('pilot.task.started', {
        pilot_session_id: get().pilotSessionId,
        scenario_id: scenarioId,
        task_id: taskId,
      });
    },

    completeTask: () => {
      const { taskId, activeScenarioId, taskStartedAt, pilotSessionId } = get();
      if (!taskId) return;
      const durationMs = taskStartedAt ? Date.now() - new Date(taskStartedAt).getTime() : undefined;
      sendPilotEvent('pilot.task.completed', {
        pilot_session_id: pilotSessionId,
        scenario_id: activeScenarioId,
        task_id: taskId,
        duration_ms: durationMs,
      });
      set({ activeScenarioId: null, taskId: null, taskStartedAt: null });
    },

    abandonTask: () => {
      const { taskId, activeScenarioId, taskStartedAt, pilotSessionId } = get();
      if (!taskId) return;
      const durationMs = taskStartedAt ? Date.now() - new Date(taskStartedAt).getTime() : undefined;
      sendPilotEvent('pilot.task.abandoned', {
        pilot_session_id: pilotSessionId,
        scenario_id: activeScenarioId,
        task_id: taskId,
        duration_ms: durationMs,
      });
      set({ activeScenarioId: null, taskId: null, taskStartedAt: null });
    },
  };
});
