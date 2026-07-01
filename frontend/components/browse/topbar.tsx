"use client";

import { Images, LogOut, Settings, User } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { DropdownMenu, DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { useLogout } from "@/hooks/useAuth";
import { useMe } from "@/hooks/useMe";
import { cn } from "@/lib/utils";
import { SafeModeToggle } from "./safe-mode-toggle";
import { SearchBox } from "./search-box";
import { TagDrawer } from "./tag-drawer";

/** Top bar: glassmorphism + scroll-aware hide/reveal (PRD F1).
 *  Hides on scroll-down, reappears on scroll-up / hover / at top. */
export function Topbar() {
  const me = useMe();
  const logout = useLogout();
  const router = useRouter();
  const [hidden, setHidden] = useState(false);
  const [hovering, setHovering] = useState(false);

  useEffect(() => {
    let last = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      if (y < 8 || y < last) setHidden(false);
      else if (y > last + 8 && !hovering) setHidden(true);
      last = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [hovering]);

  return (
    <header
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      className={cn(
        "fixed top-0 inset-x-0 z-40 h-14 border-b border-border backdrop-blur-md bg-background/70 transition-all duration-200 ease-out-soft",
        hidden && !hovering ? "-translate-y-full opacity-0" : "translate-y-0 opacity-100",
      )}
    >
      <div className="h-full mx-auto max-w-[1800px] px-4 flex items-center gap-3">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold text-foreground shrink-0"
          aria-label="图库首页"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-accent/15 text-accent">
            <Images className="h-4 w-4" />
          </span>
          <span className="hidden sm:inline">PM Gallery</span>
        </Link>
        <TagDrawer />
        <SearchBox />
        <SafeModeToggle />
        <DropdownMenu
          align="end"
          aria-label="账户菜单"
          trigger={<User className="h-5 w-5" />}
        >
          <div className="px-3 py-2 text-xs text-muted border-b border-border mb-1">
            {me.data?.username ?? "未登录"}
          </div>
          <DropdownMenuItem
            className="flex items-center gap-2"
            onClick={() => router.push("/settings")}
          >
            <Settings className="h-4 w-4" />
            设置
          </DropdownMenuItem>
          <DropdownMenuItem
            className="flex items-center gap-2 text-explicit"
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
          >
            <LogOut className="h-4 w-4" />
            退出登录
          </DropdownMenuItem>
        </DropdownMenu>
      </div>
    </header>
  );
}
