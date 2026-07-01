"use client";

import Link from "next/link";
import { SafeModeToggle } from "@/components/browse/safe-mode-toggle";
import { useMe } from "@/hooks/useMe";

export default function SettingsPage() {
  const me = useMe();
  return (
    <main className="min-h-dvh p-6">
      <div className="max-w-2xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">设置</h1>
          <Link href="/" className="text-sm text-muted hover:text-foreground">
            ← 返回图库
          </Link>
        </header>
        <section className="rounded-xl border border-border bg-surface p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">安全模式</p>
              <p className="text-sm text-muted">
                开启后仅显示 safe 分级图片（后端按会话注入，默认开启）。
              </p>
            </div>
            <SafeModeToggle />
          </div>
          <p className="text-xs text-muted">
            当前会话状态：{me.data ? (me.data.safe_mode ? "已开启" : "已关闭") : "未登录"}
          </p>
        </section>
      </div>
    </main>
  );
}
