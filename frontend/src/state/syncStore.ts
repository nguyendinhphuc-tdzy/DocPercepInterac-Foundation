import { create } from 'zustand';

interface SyncState {
  activeElementId: string | null;
  setActive: (id: string | null) => void;
}

export const useSyncStore = create<SyncState>((set) => ({
  activeElementId: null,
  setActive: (id) => set({ activeElementId: id }),
}));
