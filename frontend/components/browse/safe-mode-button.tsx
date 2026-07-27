"use client";

import { Shield } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { useUpdateSafeMode } from "@/hooks/useUpdateSafeMode";
import { cn } from "@/lib/utils";

interface SafeModeButtonProps {
  /** bar = 桌面顶栏胶囊（md+ 才显示）；chip = 移动 chips 行的小胶囊
   *  （开 = 渐变淡紫底表达状态，关 = 描边）。逻辑完全同一份。 */
  variant?: "bar" | "chip";
}

/** 安全模式开关：点击 PATCH /me/settings。乐观翻转 + posts 失效由
 *  useUpdateSafeMode 内部处理，这里只补成功 Toast。
 *  aria-label 保持稳定，用 aria-pressed 表达开关态（component-guidelines）。 */
export default function SafeModeButton({ variant = "bar" }: SafeModeButtonProps) {
  const me = useMe();
  const update = useUpdateSafeMode();
  // 新会话服务端默认开启，未拿到 /me 前按"开"展示。
  const on = me.data?.safe_mode ?? true;

  return (
    <button
      type="button"
      aria-label="安全模式"
      aria-pressed={on}
      disabled={!me.data || update.isPending}
      onClick={() => {
        const next = !on;
        update.mutate(
          { safe_mode: next },
          { onSuccess: () => toast.success(next ? "安全模式已开启" : "安全模式已关闭") },
        );
      }}
      className={cn(
        "shrink-0 cursor-pointer items-center rounded-pill font-medium transition duration-150 ease-out-soft hover:brightness-110 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100",
        variant === "bar"
          ? "hidden h-[38px] gap-[7px] border border-accent-soft-edge bg-grad-accent-soft px-[15px] text-[13px] text-accent-soft-fg md:flex"
          : cn(
              "inline-flex h-[29px] gap-1 border px-[11px] text-[11.5px]",
              on
                ? "border-accent-soft-edge bg-grad-accent-soft text-accent-soft-fg"
                : "border-strong text-secondary",
            ),
      )}
    >
      <Shield size={variant === "bar" ? 17 : 13} aria-hidden />
      {variant === "bar" ? `安全模式：${on ? "开" : "关"}` : `安全:${on ? "开" : "关"}`}
    </button>
  );
}
