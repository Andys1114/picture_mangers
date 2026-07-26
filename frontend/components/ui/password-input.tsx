"use client";

import { Eye, EyeOff } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";
import { Input } from "./input";

/** Password input with a show/hide toggle (spec: password-toggle).
 *  The toggle is a real <button> with aria-label/aria-pressed, not a div. */
const PasswordInput = React.forwardRef<
  HTMLInputElement,
  React.ComponentProps<"input">
>(({ className, ...props }, ref) => {
  const [show, setShow] = React.useState(false);
  return (
    <div className="relative">
      <Input
        ref={ref}
        type={show ? "text" : "password"}
        className={cn("pr-11", className)}
        {...props}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        aria-label={show ? "隐藏密码" : "显示密码"}
        aria-pressed={show}
        className="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-pill text-muted transition duration-150 ease-out-soft hover:text-primary cursor-pointer active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {show ? (
          <EyeOff className="h-4 w-4" aria-hidden />
        ) : (
          <Eye className="h-4 w-4" aria-hidden />
        )}
      </button>
    </div>
  );
});
PasswordInput.displayName = "PasswordInput";

export { PasswordInput };
