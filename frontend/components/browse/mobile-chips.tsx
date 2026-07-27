"use client";

import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import FilterDrawer from "./filter-drawer";
import RailChips from "./filter-rail/rail-chips";
import SafeModeButton from "./safe-mode-button";
import { useFilterParams } from "./use-filter-params";

interface MobileChipsProps {
  /** 当前条件的 meta.total，透传给抽屉的"应用筛选 · 显示 N 张"。 */
  total?: number;
}

/** 移动 chips 行（<768，final-mobile 首屏）：横向滚动——「筛选·N」渐变 chip
 *  （N = 当前条件数，点开底部筛选抽屉）+ 已选条件 chips（可删，复用
 *  rail-chips 的 bare 布局）+「安全:开/关」chip（同 safe-mode-button 逻辑）。 */
export default function MobileChips({ total }: MobileChipsProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { tags, ratings } = useFilterParams();
  const count = tags.length + ratings.length;

  return (
    <>
      <div className="-mx-3 flex items-center gap-1.5 overflow-x-auto px-3 [-ms-overflow-style:none] [scrollbar-width:none] md:hidden [&::-webkit-scrollbar]:hidden">
        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          className="inline-flex h-[29px] shrink-0 cursor-pointer items-center gap-[5px] rounded-pill border border-accent-soft-edge bg-grad-accent-soft px-3 text-[11.5px] font-medium text-accent-soft-fg transition duration-150 ease-out-soft hover:brightness-110 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <SlidersHorizontal size={13} aria-hidden />
          {count > 0 ? `筛选 · ${count}` : "筛选"}
        </button>
        <RailChips bare />
        <SafeModeButton variant="chip" />
      </div>
      <FilterDrawer open={drawerOpen} onOpenChange={setDrawerOpen} total={total} />
    </>
  );
}
