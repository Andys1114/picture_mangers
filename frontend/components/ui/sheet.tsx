"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

/** Minimal radix-free side sheet (drawer). Backdrop click + Esc close.
 *  Focus moves to the panel on open. Full focus-trap is deferred — this is a
 *  shell for slice 1 (tag drawer data lands in #7). */
interface SheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  side?: "left" | "right";
  className?: string;
  children: React.ReactNode;
  "aria-label"?: string;
}

export function Sheet({
  open,
  onOpenChange,
  side = "left",
  className,
  children,
  ...aria
}: SheetProps) {
  const panelRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <div className="fixed inset-0 z-50">
      <div
        className="absolute inset-0 bg-black/60 animate-fade-in"
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        className={cn(
          "absolute top-0 bottom-0 w-80 max-w-[85vw] bg-background border-border shadow-xl outline-none flex flex-col",
          side === "left" ? "left-0 border-r" : "right-0 border-l",
          className,
        )}
        {...aria}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
