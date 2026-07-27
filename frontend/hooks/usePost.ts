"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";

/** 单图详情（GET /api/posts/{id}）：灯箱信息浮层的数据源。
 *  直达（无列表上下文）与会话内打开统一走这条路，不依赖列表缓存。 */
export function usePost(id: number) {
  return useQuery({
    queryKey: queryKeys.post(id),
    queryFn: () => api.getPost(id),
    staleTime: 60_000,
  });
}
