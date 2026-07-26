import * as React from "react";
import { cn } from "@/lib/utils";

/** 胶囊输入框：玻璃填充底；聚焦 = 紫边框 + 3px 光圈（设计稿登录页定稿态）。 */
const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      type={type}
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-pill border border-border-pop bg-fill-2 px-4 text-sm text-primary placeholder:text-muted transition duration-150 ease-out-soft focus:outline-none focus:border-ring focus:shadow-focus-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
