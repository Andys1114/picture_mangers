import { Images } from "lucide-react";
import { cn } from "@/lib/utils";

interface AuthCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

/** Shared shell for the login/setup pages: ambient accent glow background +
 *  branded wordmark + a frosted card. Purely presentational. */
export function AuthCard({ title, description, children, footer, className }: AuthCardProps) {
  return (
    <main className="relative min-h-dvh flex flex-col items-center justify-center p-4">
      {/* Ambient accent glow — sits behind content, never competes with it. */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,hsl(var(--accent)/0.12),transparent_55%)]"
      />
      <div className="w-full flex flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
              <Images aria-hidden className="h-5 w-5" />
            </span>
            <span className="text-lg font-semibold tracking-tight">PM Gallery</span>
          </div>
          <p className="text-sm text-muted">个人图库 · 深色沉浸式画廊</p>
        </div>
        <div
          className={cn(
            "w-full max-w-sm rounded-xl border border-border bg-surface/80 backdrop-blur shadow-e2 p-7",
            className,
          )}
        >
          <div className="mb-5">
            <h1 className="text-xl font-semibold">{title}</h1>
            {description && <p className="text-sm text-muted mt-1">{description}</p>}
          </div>
          {children}
        </div>
        {footer && <div className="text-sm text-muted">{footer}</div>}
      </div>
    </main>
  );
}
