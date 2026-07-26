import { cn } from "@/lib/utils";

interface AuthCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

/** Shared shell for the login/setup pages: ambient neon glow background +
 *  branded wordmark + a frosted glass card. Purely presentational.
 *  （D6 阶段按设计稿登录屏做整体换皮，这里先对齐令牌。） */
export function AuthCard({ title, description, children, footer, className }: AuthCardProps) {
  return (
    <main className="bg-ambient relative flex min-h-dvh flex-col items-center justify-center p-4">
      <div className="flex w-full flex-col items-center gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex flex-col items-center gap-2.5">
            <span aria-hidden className="h-11 w-11 rounded-pill bg-grad-accent shadow-glow" />
            <span className="font-brand text-xl font-bold">PM Gallery</span>
          </div>
          <p className="text-sm text-muted">个人图库 · 深色沉浸画廊</p>
        </div>
        <div
          className={cn(
            "glass-pop w-full max-w-sm rounded-modal p-7",
            className,
          )}
        >
          <div className="mb-5">
            <h1 className="text-lg font-bold">{title}</h1>
            {description && <p className="mt-1 text-sm text-muted">{description}</p>}
          </div>
          {children}
        </div>
        {footer && <div className="text-sm text-faint">{footer}</div>}
      </div>
    </main>
  );
}
