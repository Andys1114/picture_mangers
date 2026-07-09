"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/** Minimal radix-free dropdown. Trigger is a real button; the menu closes on
 *  outside click, Esc, or item selection. Keyboard: focus moves to the first
 *  item on open, ArrowUp/Down cycle items, Esc/selection restore the trigger. */
interface DropdownMenuProps {
  trigger: React.ReactNode;
  "aria-label"?: string;
  children: React.ReactNode;
  align?: "start" | "end";
  className?: string;
}

export function DropdownMenu({
  trigger,
  "aria-label": ariaLabel,
  children,
  align = "end",
  className,
}: DropdownMenuProps) {
  const [open, setOpen] = React.useState(false);
  const wrapRef = React.useRef<HTMLDivElement>(null);
  const triggerRef = React.useRef<HTMLButtonElement>(null);
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false); // no focus restore: the user has clicked elsewhere
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    menuRef.current
      ?.querySelector<HTMLElement>('[role="menuitem"]:not(:disabled)')
      ?.focus();
  }, [open]);

  const onMenuKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLElement>(
        '[role="menuitem"]:not(:disabled)',
      ) ?? [],
    );
    if (items.length === 0) return;
    const idx = items.indexOf(document.activeElement as HTMLElement);
    const step = e.key === "ArrowDown" ? 1 : -1;
    const next =
      idx === -1
        ? step === 1
          ? 0
          : items.length - 1
        : (idx + step + items.length) % items.length;
    items[next]?.focus();
  };

  return (
    <div ref={wrapRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-label={ariaLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center justify-center h-10 w-10 rounded-md text-foreground hover:bg-surface cursor-pointer transition duration-150 ease-out-soft active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        {trigger}
      </button>
      {open && (
        <div
          ref={menuRef}
          role="menu"
          className={cn(
            "absolute top-11 z-50 min-w-[12rem] rounded-md border border-border bg-background shadow-e2 animate-fade-in p-1",
            align === "end" ? "right-0" : "left-0",
            className,
          )}
          onClick={() => {
            setOpen(false);
            triggerRef.current?.focus();
          }}
          onKeyDown={onMenuKeyDown}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export function DropdownMenuItem({
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      role="menuitem"
      className={cn(
        // No disabled:pointer-events-none: a disabled native button swallows the
        // click itself, so the menu-level onClick close doesn't fire through it.
        "w-full text-left rounded-sm px-3 py-2 text-sm text-foreground hover:bg-surface active:bg-surface/70 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        className,
      )}
      {...props}
    />
  );
}
