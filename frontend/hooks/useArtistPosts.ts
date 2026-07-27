"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";

/** 灯箱作者区"该作者更多"缩略图：按作者标签名取前几张
 *  （多取 1 张以便剔除当前图后仍能凑满 4 格）。 */
const ARTIST_PREVIEW_LIMIT = 5;

export function useArtistPosts(name: string) {
  return useQuery({
    queryKey: queryKeys.artistPosts(name),
    queryFn: () => api.listPosts({ tags: name, limit: ARTIST_PREVIEW_LIMIT }),
    staleTime: 60_000,
  });
}
