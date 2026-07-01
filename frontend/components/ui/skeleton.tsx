import { cn } from "@/lib/utils";

/** Shimmer placeholder for loading states (progressive-loading guideline). */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-surface", className)}
      {...props}
    />
  );
}

export { Skeleton };
