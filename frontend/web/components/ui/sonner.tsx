"use client";

import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      theme="dark"
      richColors
      closeButton
      toastOptions={{
        style: {
          background: "rgba(9,9,11,0.92)",
          border: "1px solid rgba(255,255,255,0.12)",
          color: "rgba(255,255,255,0.92)",
        },
      }}
    />
  );
}

