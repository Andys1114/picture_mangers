import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/** 列结构与 masonry-grid 断点对齐（2 → md 3 → lg 4）；块高错落 +
 *  shimmer 动画延迟错峰，取自 final-states.dc.html 的骨架屏。 */
const COLUMNS: { blocks: [height: number, delayMs: number][]; visibility: string }[] = [
  { blocks: [[280, 0], [180, 150], [220, 300]], visibility: "flex" },
  { blocks: [[200, 300], [260, 100], [170, 200]], visibility: "flex" },
  { blocks: [[240, 450], [190, 250], [260, 0]], visibility: "hidden md:flex" },
  { blocks: [[170, 200], [290, 500], [200, 350]], visibility: "hidden lg:flex" },
];

/** 首屏加载骨架：内容区 4 列瀑布流微光块（shimmer 1.6s 令牌）。 */
export default function MasonrySkeleton() {
  return (
    <div className="flex items-start gap-1.5" role="status" aria-label="正在加载图片">
      {COLUMNS.map((col, ci) => (
        <div key={ci} className={cn("min-w-0 flex-1 flex-col gap-1.5", col.visibility)}>
          {col.blocks.map(([height, delay], ri) => (
            <Skeleton
              key={ri}
              className="w-full"
              style={{ height, animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
