"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/** Minimal radix-free side sheet (drawer). Backdrop click + Esc close.
 *  Focus moves to the panel on open, Tab is trapped inside the panel, and
 *  focus is restored to the opener on close. */
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
    const opener =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
      if (e.key === "Tab") {
        const focusables = panelRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (!focusables || focusables.length === 0) {
          // Empty drawer state: keep focus on the panel itself.
          e.preventDefault();
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        // Initial state: the panel itself holds focus — Shift+Tab would
        // otherwise walk backwards out of the trap.
        if (e.shiftKey && (document.activeElement === first || document.activeElement === panelRef.current)) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      opener?.focus();
    };
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
          "absolute top-0 bottom-0 w-80 max-w-[85vw] bg-background border-border shadow-e2 outline-none flex flex-col",
          side === "left"
            ? "left-0 border-r animate-slide-in-left"
            : "right-0 border-l animate-slide-in-right",
          className,
        )}
        {...aria}
      >
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          aria-label="关闭"
          className="absolute top-3 right-3 z-10 flex h-8 w-8 items-center justify-center rounded-md text-muted hover:text-foreground hover:bg-surface active:scale-[0.97] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          <X className="h-4 w-4" aria-hidden />
        </button>
        {children}
      </div>
    </div>,
    document.body,
  );
}
