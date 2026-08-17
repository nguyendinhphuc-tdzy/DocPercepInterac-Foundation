import { create } from 'zustand';
import { processDocuments, patchElement, ApiError } from '../api/client';
import type { EditHistoryEntry, ElementRowData, MappedEntry } from '../types/element';

const SOURCE_EXTENSIONS = ['xlsx', 'pdf'];
const TARGET_EXTENSIONS = ['docx'];

function extensionOf(file: File): string {
  return file.name.split('.').pop()?.toLowerCase() ?? '';
}

interface WorkspaceState {
  // Document intake — no separate screen: files are added directly from
  // DocumentPane's empty state via addDocument(), which routes each file
  // to source or target by extension (matches api/routes/process.py's own
  // SOURCE_FORMATS/TARGET_FORMATS) so the user never has to categorize
  // anything by hand.
  sourceFiles: File[];
  targetFiles: File[];
  intakeError: string | null;
  addDocument: (file: File) => void;
  removeSourceFile: (index: number) => void;
  removeTargetFile: (index: number) => void;
  resetWorkspace: () => void;

  // Processing (POST /api/process) — see src/api/client.ts
  processId: string | null;
  processingStatus: 'idle' | 'processing' | 'done' | 'error';
  processingError: string | null;
  sourceElements: ElementRowData[];
  targetElements: ElementRowData[];
  mapped: MappedEntry[];
  downloadUrl: string | null;
  runProcessing: () => Promise<void>;

  // Live editing (PATCH /api/elements/<id>) — writes directly into the
  // output document at the edited element's Anchor. Editing UI state
  // (which cell is open) lives locally in EditableText, not here.
  editError: string | null;
  editTargetElement: (index: number, newValue: string) => Promise<void>;

  // Undo — session-only stack of prior values (see EditHistoryEntry).
  // Each undo is itself just another PATCH with the previous value, so it
  // gets its own lineage record too (mapping/lineage.py) — this stack
  // only exists to know what "previous" means, not as the source of truth.
  editHistory: EditHistoryEntry[];
  isUndoing: boolean;
  undoLastEdit: () => Promise<void>;

  // Cross-pane "related element" highlighting — set on hover in
  // DocumentPane/ElementsPane/ResultsPane, read by all three so hovering
  // one view highlights (and scrolls to) the same element elsewhere.
  hoveredElementIndex: number | null;
  setHoveredElement: (index: number | null) => void;
}

const initialWorkspaceState = {
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

  addDocument: (file) => {
    const ext = extensionOf(file);
    if (TARGET_EXTENSIONS.includes(ext)) {
      // Only one target at a time — a new one replaces the previous
      // pending selection (matches the backend: exactly one docx output).
      set({ targetFiles: [file], intakeError: null });
    } else if (SOURCE_EXTENSIONS.includes(ext)) {
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
  resetWorkspace: () => set({ ...initialWorkspaceState }),

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
      });
    } catch (err) {
      set({
        processingStatus: 'error',
        processingError: err instanceof ApiError ? err.message : 'Unexpected error while processing documents.',
      });
    }
  },

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
      // Revert the optimistic update — the output file was never written.
      set({
        targetElements: previousElements,
        editError: err instanceof ApiError ? err.message : 'Failed to save edit.',
      });
    }
  },

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
      // Revert the optimistic undo and put the entry back so it can be retried.
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
