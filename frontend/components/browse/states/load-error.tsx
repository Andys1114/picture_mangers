"use client";

import { CloudOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LoadErrorProps {
  error: unknown;
  onRetry: () => void;
}

/** 加载失败：cause + recovery 文案 + mono 技术细节（ApiError.message
 *  或原生错误信息）+ 渐变重试按钮（refetch）。 */
export default function LoadError({ error, onRetry }: LoadErrorProps) {
  const detail = error instanceof Error ? error.message : String(error);

  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center gap-3.5 py-28 text-center"
    >
      <span className="flex h-[72px] w-[72px] items-center justify-center rounded-pill border border-explicit-edge bg-explicit-soft">
        <CloudOff size={32} className="text-explicit" aria-hidden />
      </span>
      <p className="text-[17px] font-bold">加载失败</p>
      <p className="text-[13px] text-muted">请检查后端是否运行，然后重试。</p>
      <code className="rounded-thumb border border-divider bg-black/40 px-3 py-1.5 font-mono text-[11px] text-faint">
        {detail}
      </code>
      <Button className="mt-1" onClick={onRetry}>
        <RefreshCw size={16} aria-hidden />
        重试
      </Button>
    </div>
  );
}
