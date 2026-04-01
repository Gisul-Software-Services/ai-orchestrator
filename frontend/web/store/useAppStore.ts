"use client";

import { create } from "zustand";

export type ThemeMode = "dark" | "light";

interface AppState {
  orgFilter: string | null;
  setOrgFilter: (orgId: string | null) => void;

  // Simple client-side flag; server auth still enforced by cookie + middleware.
  isAuthenticated: boolean;
  setAuthenticated: (value: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  orgFilter: null,
  setOrgFilter: (orgId) => set({ orgFilter: orgId }),
  isAuthenticated: false,
  setAuthenticated: (value) => set({ isAuthenticated: value }),
}));

