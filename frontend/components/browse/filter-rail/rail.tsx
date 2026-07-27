"use client";

import { ChevronLeft, ChevronRight, Pin, Shield, Tag as TagIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import RailChips from "./rail-chips";
import RailRatings from "./rail-ratings";
import RailTags from "./rail-tags";
import { useAutoCollapse } from "./use-auto-collapse";
import { useFilterParams } from "../use-filter-params";

const ICON_BTN =
  "flex cursor-pointer items-center justify-center rounded-pill transition duration-150 ease-out-soft active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** 左侧筛选栏：240px 玻璃圆角卡（radius 20），仅桌面（md+）；<768 整体隐藏，
 *  由 chips 行的「筛选」chip 唤起底部抽屉（filter-drawer）替代。
 *  无操作 8s 自动折叠为 56px 竖向图标条（悬停/聚焦展开），图钉常驻；
 *  宽度 240↔56px 220ms，缓动走令牌（reduced-motion 由 globals 全局关闭）。 */
export default function FilterRail() {
  const { collapsed, pinned, expand, collapse, togglePin, containerProps } =
    useAutoCollapse();
  const { tags } = useFilterParams();

  return (
    <aside
      aria-label="筛选栏"
      {...containerProps}
      className={cn(
        "glass-bar sticky top-[86px] shrink-0 overflow-hidden transition-[width,border-radius] duration-220 ease-out-soft max-md:hidden",
        collapsed ? "w-14 rounded-pill" : "w-60 rounded-panel",
      )}
    >
      {collapsed ? (
        <div className="flex flex-col items-center gap-2 py-3">
          <button
            type="button"
            aria-label="展开筛选栏"
            onClick={expand}
            className={cn(ICON_BTN, "h-9 w-9 bg-fill-2 text-muted hover:bg-fill-3 hover:text-primary")}
          >
            <ChevronRight size={17} aria-hidden />
          </button>
          <span aria-hidden className="h-px w-6 bg-divider" />
          <button
            type="button"
            aria-label="展开标签筛选"
            onClick={expand}
            className={cn(
              ICON_BTN,
              "relative h-9 w-9",
              tags.length > 0
                ? "border border-accent-soft-edge bg-grad-accent-soft text-accent-soft-fg"
                : "text-muted hover:bg-fill-2 hover:text-primary",
            )}
          >
            <TagIcon size={17} aria-hidden />
            {tags.length > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-pill bg-accent-from font-mono text-[9px] font-bold text-accent-fg">
                {tags.length}
              </span>
            )}
          </button>
          <button
            type="button"
            aria-label="展开评级筛选"
            onClick={expand}
            className={cn(ICON_BTN, "h-9 w-9 text-muted hover:bg-fill-2 hover:text-primary")}
          >
            <Shield size={17} aria-hidden />
          </button>
        </div>
      ) : (
        <div className="flex w-60 flex-col gap-[15px] p-4">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold">筛选</h2>
            <span className="flex-1" />
            <button
              type="button"
              aria-label="图钉常驻"
              aria-pressed={pinned}
              onClick={togglePin}
              className={cn(
                ICON_BTN,
                "h-7 w-7",
                pinned
                  ? "border border-accent-soft-edge bg-grad-accent-soft text-accent-soft-fg"
                  : "bg-fill-2 text-muted hover:bg-fill-3 hover:text-primary",
              )}
            >
              <Pin size={15} aria-hidden />
            </button>
            <button
              type="button"
              aria-label="折叠筛选栏"
              onClick={collapse}
              className={cn(ICON_BTN, "h-7 w-7 bg-fill-2 text-muted hover:bg-fill-3 hover:text-primary")}
            >
              <ChevronLeft size={16} aria-hidden />
            </button>
          </div>
          <p className="-mt-[9px] text-[11px] text-faint">无操作 8 秒后自动折叠</p>
          <RailChips />
          <div aria-hidden className="h-px bg-divider" />
          <RailTags />
          <div aria-hidden className="h-px bg-divider" />
          <RailRatings />
        </div>
      )}
    </aside>
  );
}
