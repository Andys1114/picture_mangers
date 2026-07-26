import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/** 胶囊 chip 基座：分类 chip / 评级 chip 的样式底（mono 字体、999 圆角）。
 *  分类/评级三件套类名由 lib/colors.ts 经 className 注入。 */
const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 font-mono text-xs font-medium transition-colors duration-150 ease-out-soft",
  {
    variants: {
      variant: {
        default: "bg-fill-2 border-border text-secondary",
        outline: "border-strong bg-transparent text-secondary",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
