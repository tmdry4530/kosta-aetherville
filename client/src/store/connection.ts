import type { WorldStatePayload } from '@aetherville/shared-schemas';
import { create } from 'zustand';

export type ConnectionState = 'idle' | 'connecting' | 'connected' | 'replay' | 'error';

interface ConnectionStore {
  state: ConnectionState;
  lastTick: number;
  lastWorldState: WorldStatePayload | null;
  setState: (state: ConnectionState) => void;
  applyWorldState: (tick: number, worldState: WorldStatePayload) => void;
  applyReplayWorldState: (tick: number, worldState: WorldStatePayload) => void;
}

export const useConnectionStore = create<ConnectionStore>((set) => ({
  state: 'idle',
  lastTick: 0,
  lastWorldState: null,
  setState: (state) => set({ state }),
  applyWorldState: (lastTick, lastWorldState) => set({ lastTick, lastWorldState, state: 'connected' }),
  applyReplayWorldState: (lastTick, lastWorldState) => set({ lastTick, lastWorldState, state: 'replay' })
}));
