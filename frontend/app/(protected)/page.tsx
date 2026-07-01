"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { MasonryGrid } from "@/components/browse/masonry-grid";
import { useInfinitePosts } from "@/hooks/useInfinitePosts";

function BrowseView() {
  const params = useSearchParams();
  const tags = params.get("tags") ?? undefined;
  const q = useInfinitePosts({ tags });
  return (
    <MasonryGrid
      pages={q.data?.pages.map((p) => p.data) ?? []}
      isLoading={q.isLoading}
      isFetchingNextPage={q.isFetchingNextPage}
      hasNextPage={!!q.hasNextPage}
      fetchNextPage={() => q.fetchNextPage()}
    />
  );
}

export default function BrowsePage() {
  return (
    <main className="pb-8">
      <Suspense fallback={<div className="p-8 text-muted">加载中…</div>}>
        <BrowseView />
      </Suspense>
    </main>
  );
}
