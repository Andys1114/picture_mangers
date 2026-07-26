"use client";

import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import type { Me } from "@/lib/types";

/** Current user + per-session safe_mode. 401 (no session) resolves to null
 *  so the providers layer can redirect to /login without surfacing an error. */
export function useMe() {
  return useQuery<Me | null>({
    queryKey: queryKeys.me(),
    queryFn: async () => {
      try {
        return await api.me();
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) return null;
        throw err;
      }
    },
    retry: false,
    staleTime: Infinity,
  });
}
