"use client";

import { Suspense } from "react";
import FilterRail from "@/components/browse/filter-rail/rail";
import Topbar from "@/components/browse/topbar";
import { useFilterParams } from "@/components/browse/use-filter-params";
import { useInfinitePosts } from "@/hooks/useInfinitePosts";

/** 浏览页主体：顶栏 + 左侧筛选栏 + 主内容两栏。
 *  主内容目前是标题行 + 临时列表占位——D3 用瀑布流（masonry-grid）接管。 */
function BrowseView() {
  const { tagsParam, ratingsParam } = useFilterParams();
  const posts = useInfinitePosts({ tags: tagsParam, ratings: ratingsParam });
  const total = posts.data?.pages[0]?.meta.total;
  const items = posts.data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div className="bg-ambient min-h-dvh">
      <Topbar />
      <div className="flex items-start gap-3.5 px-5 pb-6 pt-3.5">
        <FilterRail />
        <main className="flex min-w-0 flex-1 flex-col gap-2.5">
          <div className="flex items-baseline gap-3 px-1 pt-0.5">
            <h1 className="text-base font-bold">筛选结果</h1>
            <span className="text-[12.5px] text-muted">
              {total === undefined ? "— 张" : `${total} 张`}
            </span>
          </div>
          {/* TODO(D3)：以下为临时列表占位，勿加卡片样式。 */}
          {posts.isLoading ? (
            <p className="text-sm text-muted">正在加载…</p>
          ) : posts.isError ? (
            <p className="text-sm text-muted">加载失败，请确认后端已启动后刷新重试</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted">没有符合条件的图片</p>
          ) : (
            <ul className="flex flex-col gap-1 font-mono text-xs text-secondary">
              {items.map((p) => (
                <li key={p.id}>
                  #{p.id} · {p.width}×{p.height} · {p.rating}
                </li>
              ))}
            </ul>
          )}
        </main>
      </div>
    </div>
  );
}

export default function HomePage() {
  // useSearchParams 要求页面级 Suspense 边界（Next 预渲染约束）。
  return (
    <Suspense fallback={null}>
      <BrowseView />
    </Suspense>
  );
}
