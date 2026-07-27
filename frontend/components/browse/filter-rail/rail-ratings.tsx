"use client";

import { Check } from "lucide-react";
import { useMe } from "@/hooks/useMe";
import { ratingColor } from "@/lib/colors";
import { cn } from "@/lib/utils";
import { ALL_RATINGS, useFilterParams } from "../use-filter-params";

/** 评级勾选区：S/Q/E 多选（各自评级色），选中集序列化进 ?ratings=
 *  （全选/空 = 不带参数）。安全模式开启时整组禁用并给出说明——
 *  此时服务端强制只返回 safe，参数会被忽略。 */
export default function RailRatings() {
  const me = useMe();
  const { checkedRatings, toggleRating } = useFilterParams();
  const safeModeOn = me.data?.safe_mode ?? true;

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-mono text-[10px] font-semibold uppercase tracking-[1.5px] text-label">
        评级 RATING
      </h3>
      {ALL_RATINGS.map((r) => {
        const checked = checkedRatings.includes(r);
        return (
          <button
            key={r}
            type="button"
            role="checkbox"
            aria-checked={checked}
            disabled={safeModeOn}
            onClick={() => toggleRating(r)}
            className="flex cursor-pointer items-center gap-[9px] text-left font-mono text-[12.5px] font-medium text-secondary transition duration-150 ease-out-soft hover:text-primary active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100"
          >
            <span
              aria-hidden
              className={cn(
                "flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded border",
                checked ? ratingColor(r) : "border-strong bg-fill-1",
              )}
            >
              {checked && <Check size={11} strokeWidth={3} />}
            </span>
            {r}
          </button>
        );
      })}
      {safeModeOn && (
        <p className="text-[11px] text-faint">
          安全模式开启中，仅显示安全评级；关闭安全模式后可用
        </p>
      )}
    </div>
  );
}
