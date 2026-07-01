"use client";

import { ImageOff } from "lucide-react";
import { useEffect, useRef } from "react";
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

/** CSS-columns waterfall (PRD F1). Infinite scroll: a sentinel at the bottom
 *  triggers fetchNextPage via IntersectionObserver. Items stagger in on first
 *  render (capped — reduced-motion disables it globally via globals.css). */
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

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-muted gap-3">
        <ImageOff className="h-8 w-8" />
        <p>加载失败，请检查后端是否运行。</p>
        <Button variant="outline" size="sm" onClick={() => refetch()}>
          重试
        </Button>
      </div>
    );
  }

  const flat = pages.flat();
  if (flat.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-32 text-muted gap-2">
        <ImageOff className="h-8 w-8" />
        <p className="text-lg">这里还没有图片</p>
        <p className="text-sm">导入本地文件夹或抓取 Danbooru 后会出现在这里（待 #8）。</p>
      </div>
    );
  }

  return (
    <>
      <div className="masonry p-1">
        {flat.map((post, i) => (
          <div
            key={post.id}
            className="animate-fade-in-up"
            style={{ animationDelay: `${Math.min(i, 6) * 40}ms` }}
          >
            <PostCard post={post} />
          </div>
        ))}
      </div>
      <div ref={sentinelRef} className="h-12 flex items-center justify-center">
        {isFetchingNextPage && <Skeleton className="h-8 w-40" />}
      </div>
    </>
  );
}
