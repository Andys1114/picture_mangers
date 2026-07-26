"use client";

import { Suspense } from "react";
import FilterRail from "@/components/browse/filter-rail/rail";
import MasonryGrid from "@/components/browse/masonry-grid";
import EmptyLibrary from "@/components/browse/states/empty-library";
import LoadError from "@/components/browse/states/load-error";
import MasonrySkeleton from "@/components/browse/states/masonry-skeleton";
import NoResults from "@/components/browse/states/no-results";
import Topbar from "@/components/browse/topbar";
import { useFilterParams } from "@/components/browse/use-filter-params";
import { useInfinitePosts } from "@/hooks/useInfinitePosts";
import { ratingLabel } from "@/lib/colors";

/** 浏览页主体：顶栏 + 左侧筛选栏 + 瀑布流。内容区按状态切换：
 *  首屏骨架 → 失败重试 → 空图库（无筛选）/ 无结果（有筛选）→ 瀑布流。 */
function BrowseView() {
  const { tags, ratings, tagsParam, ratingsParam } = useFilterParams();
  const posts = useInfinitePosts({ tags: tagsParam, ratings: ratingsParam });
  const total = posts.data?.pages[0]?.meta.total;
  const pages = posts.data?.pages.map((p) => p.data) ?? [];
  const hasFilters = tags.length > 0 || ratings.length > 0;

  // 条件摘要（设计稿："12 张 · miku + … · 最新入库在前"）。
  const conditions = [...tags, ...ratings.map(ratingLabel)];
  const summary = [
    total === undefined ? "— 张" : `${total} 张`,
    ...(conditions.length > 0 ? [conditions.join(" + ")] : []),
    "最新入库在前",
  ].join(" · ");

  return (
    <div className="bg-ambient min-h-dvh">
      <Topbar />
      <div className="flex items-start gap-3.5 px-5 pb-6 pt-3.5">
        <FilterRail />
        <main className="flex min-w-0 flex-1 flex-col gap-2.5">
          <div className="flex items-baseline gap-3 px-1 pt-0.5">
            <h1 className="text-base font-bold">筛选结果</h1>
            <span className="min-w-0 truncate text-[12.5px] text-muted">{summary}</span>
          </div>
          {posts.isLoading ? (
            <MasonrySkeleton />
          ) : posts.isError ? (
            <LoadError error={posts.error} onRetry={() => posts.refetch()} />
          ) : total === 0 ? (
            hasFilters ? (
              <NoResults />
            ) : (
              <EmptyLibrary />
            )
          ) : (
            <MasonryGrid
              pages={pages}
              hasNextPage={posts.hasNextPage}
              isFetchingNextPage={posts.isFetchingNextPage}
              fetchNextPage={posts.fetchNextPage}
            />
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
