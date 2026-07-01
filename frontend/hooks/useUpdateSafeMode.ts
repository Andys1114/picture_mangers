"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import type { Me } from "@/lib/types";

/** Toggle the current session's safe_mode (server-authoritative).
 *
 *  Optimistic: flip the cached /me.safe_mode immediately and invalidate the
 *  posts list so it refetches with the new rating filter. The truth is the
 *  server response — onSuccess re-stamps the /me cache with the returned Me.
 */
export function useUpdateSafeMode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { safe_mode: boolean }) => api.updateSettings(vars),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: queryKeys.me() });
      const prev = qc.getQueryData<Me | null>(queryKeys.me());
      qc.setQueryData<Me | null>(queryKeys.me(), (old) =>
        old ? { ...old, safe_mode: vars.safe_mode } : old,
      );
      // Posts depend on the server-side safe filter; refetch every active list.
      qc.invalidateQueries({ queryKey: queryKeys.postsAll() });
      return { prev };
    },
    onError: (_e, _vars, ctx) => {
      if (ctx?.prev !== undefined) qc.setQueryData(queryKeys.me(), ctx.prev);
    },
    onSuccess: (me) => {
      qc.setQueryData<Me | null>(queryKeys.me(), me);
    },
  });
}
