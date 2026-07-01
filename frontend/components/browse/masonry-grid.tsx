"use client";

import { useEffect, useRef } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { PostCard } from "./post-card";
import type { PostSummary } from "@/lib/types";

interface MasonryGridProps {
  pages: PostSummary[][];
  isLoading: boolean;
  isFetchingNextPage: boolean;
  hasNextPage: boolean;
  fetchNextPage: () => void;
}

/** CSS-columns waterfall (PRD F1). Infinite scroll: a sentinel at the bottom
 *  triggers fetchNextPage via IntersectionObserver. */
export function MasonryGrid({
  pages,
  isLoading,
  isFetchingNextPage,
  hasNextPage,
  fetchNextPage,
}: MasonryGridProps) {
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasNextPage) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) fetchNextPage();
      },
      { rootMargin: "600px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [hasNextPage, fetchNextPage]);

  if (isLoading) {
    return (
      <div className="masonry p-1">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton key={i} className="mb-1 w-full" style={{ height: 200 + (i % 4) * 60 }} />
        ))}
      </div>
    );
  }

  const total = pages.reduce((n, p) => n + p.length, 0);
  if (total === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-muted">
        <p className="text-lg">这里还没有图片</p>
        <p className="text-sm mt-1">导入本地文件夹或抓取 Danbooru 后会出现在这里（待 #8）。</p>
      </div>
    );
  }

  return (
    <>
      <div className="masonry p-1">
        {pages.map((page, i) => (
          <div key={i} className="contents">
            {page.map((post) => (
              <PostCard key={post.id} post={post} />
            ))}
          </div>
        ))}
      </div>
      <div ref={sentinelRef} className="h-12 flex items-center justify-center">
        {isFetchingNextPage && (
          <Skeleton className="h-8 w-40" />
        )}
      </div>
    </>
  );
}
