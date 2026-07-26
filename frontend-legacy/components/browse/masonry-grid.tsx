"use client";

import { ImageOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PostCard } from "./post-card";
import type { PostSummary } from "@/lib/types";

interface MasonryGridProps {
  pages: PostSummary[][];
  isLoading: boolean;
  isError: boolean;
  isFetchingNextPage: boolean;
  hasNextPage: boolean;
  fetchNextPage: () => void;
  refetch: () => void;
}

function computeCols() {
  return window.matchMedia("(min-width: 1280px)").matches
    ? 5
    : window.matchMedia("(min-width: 1024px)").matches
      ? 4
      : window.matchMedia("(min-width: 768px)").matches
        ? 3
        : 2;
}

function useColumnCount() {
  // Lazy client init: a wrong first frame (default 4) would remount every card
  // across columns when mounting with cached data (back-nav). SSR only ever
  // renders the skeleton branch, which doesn't consume this value.
  const [cols, setCols] = useState(() =>
    typeof window === "undefined" ? 4 : computeCols(),
  );
  useEffect(() => {
    const queries = [
      window.matchMedia("(min-width: 1280px)"),
      window.matchMedia("(min-width: 1024px)"),
      window.matchMedia("(min-width: 768px)"),
    ];
    const onChange = () => setCols(computeCols());
    queries.forEach((q) => q.addEventListener("change", onChange));
    return () => queries.forEach((q) => q.removeEventListener("change", onChange));
  }, []);
  return cols;
}

/** JS greedy-column waterfall (PRD F1): each item goes into the currently
 *  shortest column by cumulative aspect ratio. Assignment is prefix-stable,
 *  so appended pages never reflow already-rendered cards. Infinite scroll:
 *  a bottom sentinel triggers fetchNextPage via IntersectionObserver, guarded
 *  against re-firing while isFetchingNextPage. Items stagger in per page
 *  (capped — reduced-motion disables it globally via globals.css). */
export function MasonryGrid({
  pages,
  isLoading,
  isError,
  isFetchingNextPage,
  hasNextPage,
  fetchNextPage,
  refetch,
}: MasonryGridProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);
  const cols = useColumnCount();

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasNextPage) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) fetchNextPage();
      },
      { rootMargin: "600px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [hasNextPage, fetchNextPage, isFetchingNextPage]);

  if (isLoading) {
    return <MasonrySkeleton />;
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-muted gap-3">
        <ImageOff className="h-8 w-8" aria-hidden />
        <p className="leading-relaxed">加载失败，请检查后端是否运行。</p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          重试
        </Button>
      </div>
    );
  }

  const items = pages.flatMap((page) =>
    page.map((post, j) => ({ post, delay: Math.min(j, 6) * 40 })),
  );
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-muted gap-2">
        <ImageOff className="h-8 w-8" aria-hidden />
        <p className="text-lg">这里还没有图片</p>
        <p className="text-sm leading-relaxed">导入本地文件夹或抓取 Danbooru 后，图片会出现在这里。</p>
      </div>
    );
  }

  const columns = Array.from({ length: cols }, () => [] as typeof items);
  const heights = new Array(cols).fill(0);
  for (const it of items) {
    const k = heights.indexOf(Math.min(...heights));
    columns[k].push(it);
    heights[k] += it.post.height / it.post.width; // 列等宽，高宽比即相对高度
  }

  return (
    <>
      <div className="flex items-start gap-1 p-1">
        {columns.map((column, ci) => (
          <div key={ci} className="flex-1 min-w-0 flex flex-col">
            {column.map((it) => (
              <div
                key={it.post.id}
                className="animate-fade-in-up"
                style={{ animationDelay: it.delay + "ms" }}
              >
                <PostCard post={it.post} />
              </div>
            ))}
          </div>
        ))}
      </div>
      <div
        ref={sentinelRef}
        className="h-12 flex items-center justify-center"
        role={isFetchingNextPage ? "status" : undefined}
        aria-label={isFetchingNextPage ? "正在加载更多" : undefined}
      >
        {isFetchingNextPage && <Skeleton className="h-8 w-40" />}
      </div>
    </>
  );
}

/** Responsive skeleton waterfall — also the home page's Suspense fallback. */
export function MasonrySkeleton() {
  const colVisibility = ["flex", "flex", "hidden md:flex", "hidden lg:flex", "hidden xl:flex"];
  return (
    <div className="flex items-start gap-1 p-1" role="status" aria-label="加载中">
      {colVisibility.map((vis, ci) => (
        <div key={ci} className={`flex-1 min-w-0 flex-col ${vis}`}>
          {Array.from({ length: 3 }).map((_, ri) => (
            <Skeleton
              key={ri}
              className="mb-1 w-full"
              style={{ height: 200 + ((ci * 3 + ri) % 4) * 60 }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
