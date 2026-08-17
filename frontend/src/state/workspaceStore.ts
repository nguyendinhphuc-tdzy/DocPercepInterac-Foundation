import { create } from 'zustand';
import { processDocuments, patchElement, ApiError } from '../api/client';
import type { EditHistoryEntry, ElementRowData, MappedEntry } from '../types/element';

const SOURCE_EXTENSIONS = ['xlsx', 'pdf'];
const TARGET_EXTENSIONS = ['docx'];

function extensionOf(file: File): string {
  return file.name.split('.').pop()?.toLowerCase() ?? '';
}

export type AppView = 'home' | 'new-task' | 'workspace' | 'history' | 'settings';
export type WorkspacePreset = 'agent' | 'inspect' | 'review' | 'compare';

export interface TaskHistoryEntry {
  id: string;
  name: string;
  fileCount: number;
  elementCount: number;
  timestamp: string;
  status: 'done' | 'error';
}

interface WorkspaceState {
  // ── Navigation ──
  currentView: AppView;
  setCurrentView: (view: AppView) => void;

  // ── Workspace layout ──
  workspacePreset: WorkspacePreset;
  setWorkspacePreset: (preset: WorkspacePreset) => void;
  activeFileIndex: number;
  setActiveFileIndex: (index: number) => void;

  // ── Task history (localStorage-backed) ──
  taskHistory: TaskHistoryEntry[];
  addTaskToHistory: (entry: TaskHistoryEntry) => void;

  // ── Document intake ──
  sourceFiles: File[];
  targetFiles: File[];
  intakeError: string | null;
  addDocument: (file: File) => void;
  removeSourceFile: (index: number) => void;
  removeTargetFile: (index: number) => void;
  resetWorkspace: () => void;

  // ── Processing (POST /api/process) ──
  processId: string | null;
  processingStatus: 'idle' | 'processing' | 'done' | 'error';
  processingError: string | null;
  sourceElements: ElementRowData[];
  targetElements: ElementRowData[];
  mapped: MappedEntry[];
  downloadUrl: string | null;
  runProcessing: () => Promise<void>;

  // ── Live editing (PATCH /api/elements/<id>) ──
  editError: string | null;
  editTargetElement: (index: number, newValue: string) => Promise<void>;

  // ── Undo ──
  editHistory: EditHistoryEntry[];
  isUndoing: boolean;
  undoLastEdit: () => Promise<void>;

  // ── Cross-pane highlighting ──
  hoveredElementIndex: number | null;
  setHoveredElement: (index: number | null) => void;
}

// Load task history from localStorage
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

const initialWorkspaceState = {
  currentView: 'home' as AppView,
  workspacePreset: 'agent' as WorkspacePreset,
  activeFileIndex: 0,
  taskHistory: loadTaskHistory(),
  sourceFiles: [] as File[],
  targetFiles: [] as File[],
  intakeError: null as string | null,
  processId: null as string | null,
  processingStatus: 'idle' as const,
  processingError: null as string | null,
  sourceElements: [] as ElementRowData[],
  targetElements: [] as ElementRowData[],
  mapped: [] as MappedEntry[],
  downloadUrl: null as string | null,
  editError: null as string | null,
  editHistory: [] as EditHistoryEntry[],
  isUndoing: false,
  hoveredElementIndex: null as number | null,
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  ...initialWorkspaceState,

  // ── Navigation ──
  setCurrentView: (view) => set({ currentView: view }),
  setWorkspacePreset: (preset) => set({ workspacePreset: preset }),
  setActiveFileIndex: (index) => set({ activeFileIndex: index }),

  // ── Task history ──
  addTaskToHistory: (entry) => {
    const updated = [entry, ...get().taskHistory.filter(t => t.id !== entry.id)].slice(0, 20);
    set({ taskHistory: updated });
    saveTaskHistory(updated);
  },

  // ── Document intake ──
  addDocument: (file) => {
    const ext = extensionOf(file);
    if (TARGET_EXTENSIONS.includes(ext)) {
      set({ targetFiles: [file], intakeError: null });
    } else if (SOURCE_EXTENSIONS.includes(ext)) {
      const { sourceFiles } = get();
      if (sourceFiles.length >= 10) {
        set({ intakeError: 'You\'ve reached the recommended limit of 10 files.' });
        return;
      }
      set((state) => ({ sourceFiles: [...state.sourceFiles, file], intakeError: null }));
    } else {
      set({
        intakeError: `"${file.name}" isn't a supported type — use .xlsx/.pdf for source data or .docx for the target document.`,
      });
    }
  },
  removeSourceFile: (index) => set((state) => ({
    sourceFiles: state.sourceFiles.filter((_, i) => i !== index)
  })),
  removeTargetFile: (index) => set((state) => ({
    targetFiles: state.targetFiles.filter((_, i) => i !== index)
  })),
  resetWorkspace: () => set({
    ...initialWorkspaceState,
    currentView: get().currentView,
    taskHistory: get().taskHistory,
  }),

  // ── Processing ──
  runProcessing: async () => {
    const { sourceFiles, targetFiles } = get();
    if (sourceFiles.length === 0 || targetFiles.length === 0) return;

    set({ processingStatus: 'processing', processingError: null });
    try {
      const result = await processDocuments(sourceFiles, targetFiles[0]);
      set({
        processingStatus: 'done',
        processId: result.process_id,
        sourceElements: result.source_elements,
        targetElements: result.target_elements,
        mapped: result.mapped,
        downloadUrl: result.download_url,
        currentView: 'workspace',
      });
      // Save to history
      get().addTaskToHistory({
        id: result.process_id,
        name: targetFiles[0].name,
        fileCount: sourceFiles.length + targetFiles.length,
        elementCount: result.target_elements.length,
        timestamp: new Date().toISOString(),
        status: 'done',
      });
    } catch (err) {
      set({
        processingStatus: 'error',
        processingError: err instanceof ApiError ? err.message : 'Unexpected error while processing documents.',
      });
    }
  },

  // ── Live editing ──
  editTargetElement: async (index, newValue) => {
    const { processId, targetElements } = get();
    const element = targetElements[index];
    if (!processId || !element || newValue === element.text) return;

    const previousElements = targetElements;
    const previousValue = element.text;
    set({
      targetElements: targetElements.map((el, i) =>
        i === index ? { ...el, text: newValue, source: 'manual' } : el
      ),
      editError: null,
    });

    try {
      const result = await patchElement(processId, element.anchor, newValue);
      set((state) => ({
        downloadUrl: result.download_url,
        editHistory: [...state.editHistory, { index, anchor: element.anchor, previousValue }],
      }));
    } catch (err) {
      set({
        targetElements: previousElements,
        editError: err instanceof ApiError ? err.message : 'Failed to save edit.',
      });
    }
  },

  // ── Undo ──
  undoLastEdit: async () => {
    const { editHistory, targetElements, processId, isUndoing } = get();
    if (editHistory.length === 0 || !processId || isUndoing) return;

    const last = editHistory[editHistory.length - 1];
    const element = targetElements[last.index];
    if (!element) return;

    const valueBeforeUndo = element.text;
    set({
      editHistory: editHistory.slice(0, -1),
      isUndoing: true,
      editError: null,
      targetElements: targetElements.map((el, i) =>
        i === last.index ? { ...el, text: last.previousValue, source: 'manual' } : el
      ),
    });

    try {
      const result = await patchElement(processId, last.anchor, last.previousValue);
      set({ downloadUrl: result.download_url, isUndoing: false });
    } catch (err) {
      set((state) => ({
        targetElements: state.targetElements.map((el, i) =>
          i === last.index ? { ...el, text: valueBeforeUndo } : el
        ),
        editHistory: [...state.editHistory, last],
        editError: err instanceof ApiError ? err.message : 'Failed to undo edit.',
        isUndoing: false,
      }));
    }
  },

  setHoveredElement: (index) => set({ hoveredElementIndex: index }),
}));
