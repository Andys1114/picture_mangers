"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";

/** 灯箱 ←→ 翻页的前后图 id（GET /api/posts/{id}/next）。
 *  全局 id 倒序、随会话安全模式过滤（key 挂 "posts" 前缀，
 *  安全模式切换时随 postsAll 一并失效）。
 *  直达场景禁翻页（prd R3）：传 enabled=false 时不发请求。 */
export function usePostNav(id: number, enabled = true) {
  return useQuery({
    queryKey: queryKeys.postNav(id),
    queryFn: () => api.getPostNav(id),
    staleTime: 60_000,
    enabled,
  });
}
