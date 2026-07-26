"use client";

import { LogOut } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuItem,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { useLogout } from "@/hooks/useAuth";
import { useMe } from "@/hooks/useMe";

/** 顶栏头像用户菜单：34px 渐变头像触发 232px glass-pop 下拉。
 *  只有用户名标题区 + 退出登录；"管理面板/设置"入口等对应子任务落地后再加。 */
export default function UserMenu() {
  const me = useMe();
  const logout = useLogout();
  const initial = (me.data?.username?.[0] ?? "?").toUpperCase();

  return (
    <DropdownMenu
      aria-label="用户菜单"
      align="end"
      triggerClassName="h-[34px] w-[34px] shrink-0"
      trigger={
        <span
          aria-hidden
          className="flex h-[34px] w-[34px] items-center justify-center rounded-pill bg-grad-avatar font-brand text-[13px] font-semibold text-white"
        >
          {initial}
        </span>
      }
    >
      <DropdownMenuLabel>
        <p className="text-[13px] font-bold text-primary">{me.data?.username ?? "…"}</p>
      </DropdownMenuLabel>
      <DropdownMenuItem
        className="text-explicit hover:text-explicit"
        disabled={logout.isPending}
        onClick={() => logout.mutate()}
      >
        <LogOut size={16} aria-hidden />
        退出登录
      </DropdownMenuItem>
    </DropdownMenu>
  );
}
