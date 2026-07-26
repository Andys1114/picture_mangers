"use client";

import { Shield } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { useUpdateSafeMode } from "@/hooks/useUpdateSafeMode";

/** 顶栏安全模式按钮：盾形图标胶囊，点击 PATCH /me/settings。
 *  乐观翻转 + posts 失效由 useUpdateSafeMode 内部处理，这里只补成功 Toast。
 *  aria-label 保持稳定，用 aria-pressed 表达开关态（component-guidelines）。 */
export default function SafeModeButton() {
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
      className="flex h-[38px] shrink-0 cursor-pointer items-center gap-[7px] rounded-pill border border-accent-soft-edge bg-grad-accent-soft px-[15px] text-[13px] font-medium text-accent-soft-fg transition duration-150 ease-out-soft hover:brightness-110 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
    >
      <Shield size={17} aria-hidden />
      安全模式：{on ? "开" : "关"}
    </button>
  );
}
