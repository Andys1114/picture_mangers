"use client";

import { Sheet } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import RailRatings from "./filter-rail/rail-ratings";
import RailTags from "./filter-rail/rail-tags";
import { useFilterParams } from "./use-filter-params";

interface FilterDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** 当前条件的 meta.total（页面 useInfinitePosts 同一查询）。筛选选择即时
   *  写 URL，页面 query 跟着刷新，所以这里的 N 天然是实时的。 */
  total?: number;
}

/** 移动筛选抽屉（<768，final-mobile 第 2 屏）：ui/sheet 底部弹层（24px 顶角 +
 *  拖动把手 + 背景压暗已内建），区块直接复用桌面 rail 的 rail-tags /
 *  rail-ratings 纯内容组件——两端共用一份实现。底部渐变按钮
 *  "应用筛选 · 显示 N 张"只负责关抽屉（条件已实时生效）。 */
export default function FilterDrawer({ open, onOpenChange, total }: FilterDrawerProps) {
  const { clearAll } = useFilterParams();

  return (
    <Sheet open={open} onOpenChange={onOpenChange} aria-label="筛选">
      <div className="flex flex-col gap-3.5 px-4 pb-2 pt-1">
        {/* 标题行：右侧 pr 给 Sheet 内建关闭钮让位 */}
        <div className="flex items-center pr-9">
          <h2 className="text-[15px] font-bold">筛选</h2>
          <button
            type="button"
            onClick={clearAll}
            className="ml-auto cursor-pointer rounded-pill px-2 py-1 text-xs font-medium text-muted transition duration-150 ease-out-soft hover:text-primary active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            清空全部
          </button>
        </div>
        <RailTags />
        <div aria-hidden className="h-px shrink-0 bg-divider" />
        <RailRatings />
      </div>
      {/* 应用按钮吸底：滚动长列表时始终可见 */}
      <div className="sticky bottom-0 mt-1 bg-glass-pop px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-2 backdrop-blur-md">
        <Button size="lg" className="w-full" onClick={() => onOpenChange(false)}>
          应用筛选 · 显示 {total === undefined ? "—" : total.toLocaleString()} 张
        </Button>
      </div>
    </Sheet>
  );
}
