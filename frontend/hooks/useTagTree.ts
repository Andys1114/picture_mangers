"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";

/** 连带树（GET /api/tags/tree），筛选栏标签成组区的数据源。
 *  标签结构只在管理操作后变化，staleTime 拉长到 5 分钟
 *  （state-management：tags 属长 stale 资源）。 */
export function useTagTree() {
  return useQuery({
    queryKey: queryKeys.tagTree(),
    queryFn: () => api.tagTree(),
    select: (res) => res.data,
    staleTime: 5 * 60_000,
  });
}
