"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";

/** Read ?next= from the URL at submit time (avoids the useSearchParams hook,
 *  which would force a Suspense boundary on the login/setup pages). */
function redirectAfterAuth(router: ReturnType<typeof useRouter>, fallback = "/") {
  if (typeof window === "undefined") {
    router.replace(fallback);
    return;
  }
  const next = new URLSearchParams(window.location.search).get("next");
  router.replace(next && next.startsWith("/") ? next : fallback);
}

/** First-run user creation. Invalidates /me so the providers layer re-fetches. */
export function useSetup() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: (vars: { username: string; password: string }) => api.setup(vars),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: queryKeys.me() });
      redirectAfterAuth(router, "/");
    },
  });
}

/** Login. Invalidates /me and returns to ?next or "/". */
export function useLogin() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: (vars: { username: string; password: string }) => api.login(vars),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: queryKeys.me() });
      redirectAfterAuth(router, "/");
    },
  });
}

/** Logout. Clears the cache (drops server state) and sends to /login. */
export function useLogout() {
  const qc = useQueryClient();
  const router = useRouter();
  return useMutation({
    mutationFn: () => api.logout(),
    onSuccess: () => {
      qc.clear();
      router.replace("/login");
    },
  });
}
