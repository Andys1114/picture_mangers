"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Sheet } from "@/components/ui/sheet";
import { ratingColor, ratingLabel, tagCategoryColor } from "@/lib/colors";
import type { Rating, TagCategory } from "@/lib/types";

const CATEGORIES: TagCategory[] = ["character", "copyright", "artist", "meta", "general"];
const RATINGS: Rating[] = ["safe", "questionable", "explicit"];

/** Temporary home for the scaffold stage — proves the /api chain works via
 *  useMe. The real browse page (topbar + filter rail + waterfall + lightbox)
 *  replaces this in later stages. */
export default function HomePage() {
  const me = useMe();
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <main className="bg-ambient flex min-h-dvh flex-col items-center gap-8 p-8">
      <div className="flex flex-col items-center gap-3 text-center">
        <h1 className="font-brand text-2xl font-bold tracking-tight">
          PM Gallery — 新前端建设中
        </h1>
        <p className="text-sm text-muted">
          {me.isLoading
            ? "正在获取当前用户…"
            : me.data
              ? `当前用户：${me.data.username}`
              : "未登录，即将跳转到登录页…"}
        </p>
      </div>

      {/* TODO(阶段 D)：删除以下"令牌样品"区 — 仅供 C 阶段浏览器目测新令牌。 */}
      <section
        aria-label="令牌样品（临时）"
        className="glass-bar flex w-full max-w-2xl flex-col gap-6 rounded-panel p-6"
      >
        <p className="font-mono text-[10px] uppercase tracking-[1.5px] text-label">
          令牌样品 · 阶段 D 移除
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <Button>渐变主按钮</Button>
          <Button variant="secondary">玻璃次按钮</Button>
          <Button variant="outline">描边胶囊</Button>
          <Button variant="ghost">幽灵按钮</Button>
          <Button variant="destructive">危险操作</Button>
          <Button disabled>禁用态</Button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {CATEGORIES.map((c) => (
            <Badge key={c} className={tagCategoryColor(c)}>
              {c}
            </Badge>
          ))}
          {RATINGS.map((r) => (
            <Badge key={r} className={ratingColor(r)}>
              {ratingLabel(r)}
            </Badge>
          ))}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Input placeholder="搜索标签，空格 = 同时满足…" aria-label="示例输入框" />
          <PasswordInput placeholder="密码" aria-label="示例密码框" />
        </div>

        <div className="flex items-center gap-3">
          <Skeleton className="h-20 w-20" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-1/3" />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <DropdownMenu
            aria-label="示例用户菜单"
            align="start"
            trigger={
              <span
                aria-hidden
                className="flex h-[34px] w-[34px] items-center justify-center rounded-pill bg-grad-avatar font-brand text-[13px] font-semibold text-white"
              >
                A
              </span>
            }
          >
            <DropdownMenuLabel>
              <p className="text-[13px] font-bold text-primary">admin</p>
              <p className="font-mono text-[10.5px] text-label">实例拥有者 · 会话 30 天</p>
            </DropdownMenuLabel>
            <DropdownMenuItem>管理面板</DropdownMenuItem>
            <DropdownMenuItem>设置</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-explicit hover:text-explicit">
              退出登录
            </DropdownMenuItem>
          </DropdownMenu>
          <Button variant="secondary" size="sm" onClick={() => setSheetOpen(true)}>
            打开底部弹层
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => toast.success("安全模式已开启")}
          >
            触发 Toast
          </Button>
        </div>
      </section>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen} aria-label="示例筛选抽屉">
        <div className="flex flex-col gap-4 px-5 pb-8 pt-2">
          <p className="text-sm font-bold">底部弹层样品</p>
          <p className="text-sm text-muted">移动筛选抽屉的容器基座（E 阶段接手势）。</p>
          <Button onClick={() => setSheetOpen(false)}>应用筛选 · 显示 12 张</Button>
        </div>
      </Sheet>
    </main>
  );
}
