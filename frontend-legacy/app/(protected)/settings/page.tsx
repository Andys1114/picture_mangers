"use client";

import { ArrowLeft, Info, LogOut, ShieldCheck, User } from "lucide-react";
import Link from "next/link";
import { SafeModeToggle } from "@/components/browse/safe-mode-toggle";
import { Button } from "@/components/ui/button";
import { useLogout } from "@/hooks/useAuth";
import { useMe } from "@/hooks/useMe";

function SectionCard({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-surface p-5 shadow-e1">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3 min-w-0">
          <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-md bg-accent/15 text-accent">
            <Icon className="h-4 w-4" aria-hidden />
          </span>
          <div className="min-w-0">
            <h2 className="font-medium">{title}</h2>
            <p className="text-sm text-muted mt-0.5 break-words leading-relaxed">
              {description}
            </p>
          </div>
        </div>
        <div className="shrink-0">{children}</div>
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const me = useMe();
  const logout = useLogout();
  return (
    <main className="relative min-h-[calc(100dvh-3.5rem)] p-6">
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,hsl(var(--accent)/0.08),transparent_55%)]"
      />
      <div className="max-w-2xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">设置</h1>
          <Link
            href="/"
            className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            返回图库
          </Link>
        </header>

        <SectionCard
          icon={ShieldCheck}
          title="安全模式"
          description="开启后仅显示分级为 safe 的图片（默认开启）。"
        >
          <SafeModeToggle />
        </SectionCard>

        <SectionCard
          icon={User}
          title="账户"
          description={me.data ? `当前用户：${me.data.username}` : "未登录"}
        >
          <Button
            variant="outline"
            onClick={() => logout.mutate()}
            disabled={logout.isPending || !me.data}
            className="text-explicit border-explicit/40 hover:bg-explicit/10 hover:text-explicit"
          >
            {logout.isPending ? (
              "退出中…"
            ) : (
              <>
                <LogOut className="h-4 w-4" aria-hidden />
                退出登录
              </>
            )}
          </Button>
        </SectionCard>

        <SectionCard
          icon={Info}
          title="关于"
          description="PM Gallery — 个人图库，本地导入 + Danbooru 抓取，深色沉浸式画廊。"
        >
          <span className="text-xs text-muted font-mono">v0.1.0</span>
        </SectionCard>
      </div>
    </main>
  );
}
