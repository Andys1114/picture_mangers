import { cn } from "@/lib/utils";

interface AuthCardProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}

/** 登录/初始化同壳（设计稿第 5 屏 + final-mobile 登录屏）：中上紫晕 +
 *  右下青晕背景，居中渐变光点 logo + 360px glass-pop 玻璃卡（radius 24）。
 *  <768：卡宽 calc(100vw-32px)、上下留白收紧且整体靠上（卡片落在视口
 *  上半部，软键盘弹出不遮字段）。纯展示。 */
export function AuthCard({ title, description, children, footer, className }: AuthCardProps) {
  return (
    <main className="bg-ambient-auth flex min-h-dvh flex-col items-center justify-center gap-[22px] p-4 max-md:justify-start max-md:gap-4 max-md:pt-10">
      <div className="flex flex-col items-center gap-[9px] text-center">
        <span aria-hidden className="h-11 w-11 rounded-pill bg-grad-accent shadow-glow" />
        <span className="font-brand text-xl font-bold">PM Gallery</span>
        <span className="text-[12.5px] text-muted">个人图库 · 深色沉浸画廊</span>
      </div>
      <div
        className={cn(
          "glass-pop w-[360px] max-w-full rounded-modal p-[26px] max-md:w-[calc(100vw-32px)] max-md:p-5",
          className,
        )}
      >
        <div className="mb-[15px] flex flex-col gap-[3px]">
          <h1 className="text-[17px] font-bold">{title}</h1>
          {description && <p className="text-[12.5px] text-muted">{description}</p>}
        </div>
        {children}
      </div>
      {footer && <div className="text-center text-xs text-faint">{footer}</div>}
    </main>
  );
}
