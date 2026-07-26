"use client";

import { useMe } from "@/hooks/useMe";

/** Temporary home for the scaffold stage — proves the /api chain works via
 *  useMe. The real browse page (topbar + filter rail + waterfall + lightbox)
 *  replaces this in later stages. */
export default function HomePage() {
  const me = useMe();
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-3 p-4 text-center">
      <h1 className="text-2xl font-semibold tracking-tight">
        PM Gallery — 新前端建设中
      </h1>
      <p className="text-sm text-muted">
        {me.isLoading
          ? "正在获取当前用户…"
          : me.data
            ? `当前用户：${me.data.username}`
            : "未登录，即将跳转到登录页…"}
      </p>
    </main>
  );
}
