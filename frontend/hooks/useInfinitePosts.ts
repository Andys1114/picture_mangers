"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys, type PostsQuery } from "@/lib/queryClient";

const PAGE_SIZE = 40;

/** Infinite waterfall feed. safe_mode is server-authoritative (injected by the
 *  backend), so the client only sends tags/order — never a rating override. */
export function useInfinitePosts(query: PostsQuery) {
  return useInfiniteQuery({
    queryKey: queryKeys.posts(query),
    queryFn: ({ pageParam }) =>
      api.listPosts({ ...query, page: pageParam, limit: PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (last) => {
      const pages = Math.ceil(last.meta.total / PAGE_SIZE);
      return last.meta.page < pages ? last.meta.page + 1 : undefined;
    },
  });
}
