import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { AgentSignal } from "@/types/market";

interface SignalState {
  signals: AgentSignal[];
  latestSignal: AgentSignal | null;

  addSignal: (signal: AgentSignal) => void;
  clearSignals: () => void;
}

export const useSignalStore = create<SignalState>()(
  subscribeWithSelector((set) => ({
    signals: [],
    latestSignal: null,

    addSignal: (signal) =>
      set((state) => ({
        signals: [signal, ...state.signals].slice(0, 100),
        latestSignal: signal,
      })),

    clearSignals: () => set({ signals: [], latestSignal: null }),
  }))
);
