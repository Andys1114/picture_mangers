"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import type { TagsParams } from "@/lib/types";

/** 标签索引（GET /api/tags，默认按 post_count 降序，服务端截断 200）。
 *  与连带树同属长 stale 资源（state-management：tags 长 stale）：5 分钟。 */
export function useTags(params: TagsParams = {}) {
  return useQuery({
    queryKey: queryKeys.tags(params),
    queryFn: () => api.listTags(params),
    select: (res) => res.data,
    staleTime: 5 * 60_000,
  });
}
