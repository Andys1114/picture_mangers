"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { MasonryGrid, MasonrySkeleton } from "@/components/browse/masonry-grid";
import { useInfinitePosts } from "@/hooks/useInfinitePosts";

function BrowseView() {
  const params = useSearchParams();
  const tags = params.get("tags") ?? undefined;
  const q = useInfinitePosts({ tags });
  return (
    <MasonryGrid
      pages={q.data?.pages.map((p) => p.data) ?? []}
      isLoading={q.isLoading}
      isError={q.isError}
      isFetchingNextPage={q.isFetchingNextPage}
      hasNextPage={!!q.hasNextPage}
      fetchNextPage={q.fetchNextPage}
      refetch={() => q.refetch()}
    />
  );
}

export default function BrowsePage() {
  return (
    <main className="pb-8 mx-auto max-w-[1800px]">
      <h1 className="sr-only">图库</h1>
      <Suspense fallback={<MasonrySkeleton />}>
        <BrowseView />
      </Suspense>
    </main>
  );
}
