"use client";

import { Eye, EyeOff } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

/** Password input with a show/hide toggle (spec: password-toggle).
 *  The toggle is a real <button> with aria-label/aria-pressed, not a div. */
const PasswordInput = React.forwardRef<
  HTMLInputElement,
  React.ComponentProps<"input">
>(({ className, ...props }, ref) => {
  const [show, setShow] = React.useState(false);
  return (
    <div className="relative">
      <input
        ref={ref}
        type={show ? "text" : "password"}
        className={cn(
          "flex h-10 w-full rounded-md border border-border bg-surface/60 px-3 py-2 pr-10 text-sm text-foreground placeholder:text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        {...props}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "隐藏密码" : "显示密码"}
        aria-pressed={show}
        className="absolute right-2 top-1/2 -translate-y-1/2 flex h-7 w-7 items-center justify-center rounded text-muted hover:text-foreground cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
});
PasswordInput.displayName = "PasswordInput";

export { PasswordInput };
