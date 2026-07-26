"use client";

import { Toaster as SonnerToaster } from "sonner";

/** Toast host. aria-live is handled by sonner; toasts don't steal focus. */
export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="bottom-right"
      toastOptions={{
        style: {
          background: "hsl(var(--surface))",
          color: "hsl(var(--foreground))",
          border: "1px solid hsl(var(--border))",
        },
      }}
    />
  );
}
