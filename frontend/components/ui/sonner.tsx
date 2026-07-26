"use client";

import { Toaster as SonnerToaster } from "sonner";

/** Toast host：底部居中玻璃胶囊（设计稿 · 交互中间态）。
 *  aria-live is handled by sonner; toasts don't steal focus. */
export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="bottom-center"
      toastOptions={{
        style: {
          background: "var(--glass-pop)",
          backdropFilter: "blur(22px)",
          WebkitBackdropFilter: "blur(22px)",
          color: "var(--text-primary)",
          border: "1px solid var(--border-pop)",
          borderRadius: "var(--radius-pill)",
          boxShadow: "var(--shadow-e2)",
          padding: "10px 18px",
          width: "auto",
        },
      }}
    />
  );
}
