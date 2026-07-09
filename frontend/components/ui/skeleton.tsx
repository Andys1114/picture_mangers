import { cn } from "@/lib/utils";

/** Shimmer placeholder for loading states (progressive-loading guideline).
 *  A slow gradient sweep reads as "loading" without a blocking spinner. */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("shimmer relative overflow-hidden rounded-md", className)}
      {...props}
    />
  );
}

export { Skeleton };
