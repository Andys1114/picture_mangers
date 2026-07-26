"use client";

import { ShieldCheck, ShieldOff } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { useUpdateSafeMode } from "@/hooks/useUpdateSafeMode";
import { cn } from "@/lib/utils";

/** Safe-mode toggle. Server-authoritative: PATCH /me/settings, then the posts
 *  list refetches with the new rating filter (injected backend-side). */
export function SafeModeToggle() {
  const me = useMe();
  const update = useUpdateSafeMode();
  const safeMode = me.data?.safe_mode ?? true;

  const onToggle = () => {
    const next = !safeMode;
    update.mutate(
      { safe_mode: next },
      {
        onSuccess: (res) =>
          toast.success(res.safe_mode ? "安全模式已开启" : "安全模式已关闭"),
        onError: () => toast.error("切换失败，请重试"),
      },
    );
  };

  const On = safeMode;
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={!me.data || update.isPending}
      aria-pressed={safeMode}
      aria-label="安全模式"
      title={safeMode ? "安全模式：仅显示 safe" : "安全模式：已关闭"}
      className={cn(
        "inline-flex items-center gap-1.5 h-10 px-3 rounded-md text-sm font-medium transition duration-150 ease-out-soft cursor-pointer active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 disabled:cursor-not-allowed",
        On ? "bg-safe/15 text-safe hover:bg-safe/25" : "bg-surface text-muted hover:text-foreground",
      )}
    >
      {On ? (
        <ShieldCheck className="h-4 w-4" aria-hidden />
      ) : (
        <ShieldOff className="h-4 w-4" aria-hidden />
      )}
      <span className="hidden sm:inline">{On ? "安全" : "全部"}</span>
    </button>
  );
}
