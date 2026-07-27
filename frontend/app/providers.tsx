"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMe } from "@/hooks/useMe";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        retry: 1,
        staleTime: 30_000,
      },
    },
  });
}

/** If /me says no session (401) and we're on a protected page, go to /login.
 *  /login and /setup manage their own flow via /api/auth/status. */
function MeGate({ children }: { children: React.ReactNode }) {
  const me = useMe();
  const pathname = usePathname();
  const router = useRouter();
  const publicRoute = pathname === "/login" || pathname === "/setup";

  useEffect(() => {
    if (!publicRoute && me.isSuccess && me.data === null) {
      const next = encodeURIComponent(pathname);
      router.replace(`/login?next=${next}`);
    }
  }, [publicRoute, me.isSuccess, me.data, pathname, router]);

  return <>{children}</>;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(makeQueryClient);
  return (
    <QueryClientProvider client={client}>
      <MeGate>{children}</MeGate>
    </QueryClientProvider>
  );
}
