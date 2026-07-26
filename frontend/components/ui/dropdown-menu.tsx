"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

/** 无 Radix 自研下拉：232px 玻璃弹层（glass-pop / 圆角 16），供用户菜单用。
 *  Trigger is a real button; the menu closes on outside click, Esc, or item
 *  selection. Keyboard: focus moves to the first item on open, ArrowUp/Down
 *  cycle items, Esc/selection restore the trigger. */
interface DropdownMenuProps {
  trigger: React.ReactNode;
  "aria-label"?: string;
  children: React.ReactNode;
  align?: "start" | "end";
  className?: string;
  /** 覆盖触发按钮样式（如头像触发时去掉默认 40px 方块）。 */
  triggerClassName?: string;
}

export function DropdownMenu({
  trigger,
  "aria-label": ariaLabel,
  children,
  align = "end",
  className,
  triggerClassName,
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
        className={cn(
          "inline-flex h-10 w-10 items-center justify-center rounded-pill text-primary transition duration-150 ease-out-soft hover:bg-fill-2 cursor-pointer active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          triggerClassName,
        )}
      >
        {trigger}
      </button>
      {open && (
        <div
          ref={menuRef}
          role="menu"
          className={cn(
            "glass-pop absolute top-12 z-50 w-[232px] rounded-table p-2 animate-fade-in",
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
        "flex w-full items-center gap-2.5 rounded-thumb-lg px-3 py-2 text-left text-[13px] font-medium text-secondary transition duration-150 ease-out-soft hover:bg-fill-2 hover:text-primary active:bg-fill-3 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  );
}

/** 菜单标题区（用户名 + 说明行，非交互）。 */
export function DropdownMenuLabel({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("mb-1 border-b border-divider px-3 pb-2.5 pt-2", className)}
      {...props}
    />
  );
}

export function DropdownMenuSeparator({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="separator"
      className={cn("mx-2 my-1 h-px bg-divider", className)}
      {...props}
    />
  );
}
