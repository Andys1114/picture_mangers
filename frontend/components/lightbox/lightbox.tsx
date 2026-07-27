"use client";

import Image from "next/image";
import { createPortal } from "react-dom";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { useQueryClient, type InfiniteData } from "@tanstack/react-query";
import InfoPanel from "./info-panel";
import { useLightboxUrl } from "./use-lightbox-url";
import { useSwipe } from "./use-swipe";
import { useFilterParams } from "@/components/browse/use-filter-params";
import { Button } from "@/components/ui/button";
import { usePost } from "@/hooks/usePost";
import { usePostNav } from "@/hooks/usePostNav";
import { mediaUrl } from "@/lib/api";
import { queryKeys } from "@/lib/queryClient";
import { cn } from "@/lib/utils";
import type { Paginated, PostSummary } from "@/lib/types";

/** 右上计数：从当前筛选的列表缓存里找序号（"12 / 1,248"）；
 *  直达（无列表上下文）或算不出序号的场景退化为 mono id（"#0012"）。 */
function useOrdinalLabel(id: number, direct: boolean): string {
  const qc = useQueryClient();
  const { tagsParam, ratingsParam } = useFilterParams();
  const cached = qc.getQueryData<InfiniteData<Paginated<PostSummary>>>(
    queryKeys.posts({ tags: tagsParam, ratings: ratingsParam }),
  );
  if (!direct && cached) {
    const flat = cached.pages.flatMap((p) => p.data);
    const idx = flat.findIndex((p) => p.id === id);
    if (idx >= 0) {
      const total = cached.pages[0].meta.total;
      return `${(idx + 1).toLocaleString()} / ${total.toLocaleString()}`;
    }
  }
  return `#${String(id).padStart(4, "0")}`;
}

/** 两侧 44px 玻璃圆形翻页钮（仅桌面；<768 用左右滑手势翻页）。 */
function NavButton({
  side,
  label,
  onClick,
}: {
  side: "left" | "right";
  label: string;
  onClick: () => void;
}) {
  const Icon = side === "left" ? ChevronLeft : ChevronRight;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      className={cn(
        "glass-bar absolute top-1/2 flex h-11 w-11 -translate-y-1/2 cursor-pointer items-center justify-center rounded-pill text-secondary transition duration-150 ease-out-soft hover:brightness-150 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:hidden",
        side === "left" ? "left-[372px]" : "right-7",
      )}
    >
      <Icon size={22} aria-hidden />
    </button>
  );
}

interface LightboxOverlayProps {
  id: number;
  /** 直达/刷新打开（无列表上下文，prd R3）：禁 ←→ 翻页——不发 /next
   *  请求、隐藏翻页钮与序号、键盘与横滑不响应（Esc/下滑关闭不受影响）。 */
  direct: boolean;
  /** URL 写操作来自外层常驻的 useLightboxUrl 实例（会话内/直达的判定
   *  依赖跨开合的观察，不能在浮层自身实例里做）。 */
  goto: (id: number) => void;
  close: () => void;
  filterTo: (name: string) => void;
}

/** 灯箱浮层主体（photoId 有值时挂载）。
 *  桌面（md+）：纯黑 + 紫晕全屏层，主图右侧偏置 + 左侧信息浮层，
 *  ←/→/Esc 键盘、遮罩点击关闭、body 滚动锁 + 简单焦点陷阱。
 *  移动（<768，final-mobile 第 3 屏）：全屏图居中 + 顶部渐变遮罩行
 *  （返回 / id·序号）+ 信息底部半层（两档收起/展开）；
 *  手势：横滑翻页、下滑关闭（信息层收起时）、信息层上拉展开。 */
function LightboxOverlay({ id, direct, goto, close, filterTo }: LightboxOverlayProps) {
  const detail = usePost(id);
  // 直达禁翻页：不发 /next；prev/next 恒空让翻页钮、←→ 键、横滑一并失效。
  const nav = usePostNav(id, !direct);
  const prevId = direct ? null : (nav.data?.prev_id ?? null);
  const nextId = direct ? null : (nav.data?.next_id ?? null);
  const ordinal = useOrdinalLabel(id, direct);
  const overlayRef = useRef<HTMLDivElement>(null);
  // 翻页时按 id 记录加载完成，避免旧图的 loaded 状态串到新图。
  const [loadedId, setLoadedId] = useState<number | null>(null);
  const loaded = loadedId === id;
  // 移动信息半层两档：false = 收起只露标题行，true = 展开成滚动面板。
  const [infoExpanded, setInfoExpanded] = useState(false);

  // 图区手势：横滑（占优且 >60px）翻页，复用 goto（replace）；直达单图
  // prev/next 为 null 时对应方向不响应。下滑（占优且 >80px）在信息层
  // 收起时关闭，展开时先收起信息层（一次一层，避免误关）。
  const stageSwipe = useSwipe({
    onSwipeLeft: nextId !== null ? () => goto(nextId) : undefined,
    onSwipeRight: prevId !== null ? () => goto(prevId) : undefined,
    onSwipeDown: () => {
      if (infoExpanded) setInfoExpanded(false);
      else close();
    },
  });

  // 打开期间：锁 body 滚动，焦点移入浮层，关闭时还原并交还给打开者。
  useEffect(() => {
    const opener =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    overlayRef.current?.focus();
    return () => {
      document.body.style.overflow = prevOverflow;
      opener?.focus();
    };
  }, []);

  // 键盘：←/→ 翻页（replace）、Esc 关闭；Tab 圈在浮层内（同 Sheet 的做法）。
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close();
      } else if (e.key === "ArrowLeft" && prevId !== null) {
        e.preventDefault();
        goto(prevId);
      } else if (e.key === "ArrowRight" && nextId !== null) {
        e.preventDefault();
        goto(nextId);
      } else if (e.key === "Tab") {
        const focusables = overlayRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (!focusables || focusables.length === 0) {
          e.preventDefault();
          return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        if (
          e.shiftKey &&
          (document.activeElement === first ||
            document.activeElement === overlayRef.current)
        ) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [close, goto, prevId, nextId]);

  return (
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="true"
      aria-label="图片详情"
      tabIndex={-1}
      className="bg-ambient-lightbox fixed inset-0 z-50 outline-none animate-fade-in"
    >
      {/* 遮罩层：点击空白处关闭（主图/浮层/按钮是它的上层兄弟，不透传）；
          触屏滑动同图区手势（swipe 判定成立时吞掉合成 click，不会串触关闭）。 */}
      <div aria-hidden className="absolute inset-0 touch-none" onClick={close} {...stageSwipe} />

      {detail.isError ? (
        <div className="glass-pop absolute left-1/2 top-1/2 flex w-80 -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-4 rounded-panel p-7 text-center">
          <p className="text-[15px] font-bold">图片加载失败</p>
          <p className="text-[12.5px] leading-relaxed text-muted">
            这张图可能已被移除，或后端暂时无法连接。
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => detail.refetch()}>
              重试
            </Button>
            <Button variant="outline" size="sm" onClick={close}>
              关闭
            </Button>
          </div>
        </div>
      ) : (
        <>
          {/* 主图：桌面 right 120px 垂直居中（radius 14 + 大阴影）；
              <768 全屏居中、无圆角阴影。翻页时按 id 换图，黑底与浮层常驻
              不闪白，加载期垫 shimmer。图区铺滑动手势 + touch-none。 */}
          <div
            className="absolute touch-none max-md:inset-0 max-md:flex max-md:items-center max-md:justify-center md:right-[120px] md:top-1/2 md:-translate-y-1/2"
            {...stageSwipe}
          >
            {detail.data ? (
              <div className="relative">
                <Image
                  key={id}
                  src={mediaUrl(detail.data.file_path)}
                  alt={`插画 #${String(id).padStart(4, "0")}`}
                  width={detail.data.width}
                  height={detail.data.height}
                  unoptimized
                  priority
                  onLoad={() => setLoadedId(id)}
                  className={cn(
                    "h-auto w-auto transition-opacity duration-300 ease-out-soft",
                    "max-md:max-h-dvh max-md:max-w-full",
                    "md:max-h-[85dvh] md:max-w-[calc(100vw-560px)] md:rounded-card md:shadow-e3",
                    loaded ? "opacity-100" : "opacity-0",
                  )}
                />
                {!loaded && (
                  <span aria-hidden className="shimmer absolute inset-0 block md:rounded-card" />
                )}
              </div>
            ) : (
              <span
                aria-hidden
                className="shimmer block max-md:h-[50dvh] max-md:w-[80vw] md:h-[70dvh] md:w-[26vw] md:rounded-card"
              />
            )}
          </div>

          {detail.data && (
            <InfoPanel
              detail={detail.data}
              direct={direct}
              onClose={close}
              onGoto={goto}
              onFilterTag={filterTo}
              mobileExpanded={infoExpanded}
              onMobileExpandedChange={setInfoExpanded}
            />
          )}

          {/* <768 顶部渐变遮罩行：返回 / "#id · n/总数" / 星标占位（子任务）。 */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-[130px] bg-gradient-to-b from-black/65 to-transparent md:hidden"
          />
          <div className="absolute inset-x-0 top-0 flex items-center gap-2 px-3 pt-[max(12px,env(safe-area-inset-top))] md:hidden">
            <button
              type="button"
              onClick={close}
              aria-label="返回"
              className="flex h-[34px] w-[34px] shrink-0 cursor-pointer items-center justify-center rounded-pill bg-black/45 text-primary backdrop-blur transition duration-150 ease-out-soft hover:bg-black/60 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ArrowLeft size={18} aria-hidden />
            </button>
            <span className="font-mono text-xs font-medium text-white/90">
              {ordinal.startsWith("#")
                ? ordinal
                : `#${String(id).padStart(4, "0")} · ${ordinal}`}
            </span>
            <span aria-hidden className="ml-auto w-[34px]" />
          </div>

          {prevId !== null && (
            <NavButton side="left" label="上一张" onClick={() => goto(prevId)} />
          )}
          {nextId !== null && (
            <NavButton side="right" label="下一张" onClick={() => goto(nextId)} />
          )}

          <span className="glass-bar absolute right-7 top-6 rounded-pill px-3.5 py-[5px] font-mono text-xs font-medium text-muted max-md:hidden">
            {ordinal}
          </span>
        </>
      )}
    </div>
  );
}

/** 灯箱挂载点：`?photoId=` URL 驱动的浮层（非独立路由，语义见
 *  CONTEXT.md"详情页"）。无参数时不渲染；刷新/直达带参数自动打开
 *  （direct=true，禁翻页）。组件本体常驻浏览页，useLightboxUrl 得以
 *  跨开合观察"会话内打开/直达"。 */
export default function Lightbox() {
  const { photoId, direct, goto, close, filterTo } = useLightboxUrl();
  if (photoId === null || typeof document === "undefined") return null;
  return createPortal(
    <LightboxOverlay
      id={photoId}
      direct={direct}
      goto={goto}
      close={close}
      filterTo={filterTo}
    />,
    document.body,
  );
}
