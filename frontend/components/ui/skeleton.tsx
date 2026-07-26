import { cn } from "@/lib/utils";

/** 骨架占位：shimmer 1.6s 线性循环（200% 背景位移，令牌见 globals.css）。 */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("shimmer rounded-card", className)} {...props} />;
}

export { Skeleton };
