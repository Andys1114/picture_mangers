"use client";

import { useEffect, useRef, useState } from "react";
import PostCard from "./post-card";
import type { PostSummary } from "@/lib/types";

interface MasonryGridProps {
  pages: PostSummary[][];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
}

/** 列数断点：桌面（≥1024）4 列、平板（≥768）3 列、其余双列
 *  （移动端精调在 E 阶段）。列宽本身是 flex-1 自适应，断点内的
 *  窗口缩放无需 JS 参与。 */
function computeCols(): number {
  return window.matchMedia("(min-width: 1024px)").matches
    ? 4
    : window.matchMedia("(min-width: 768px)").matches
      ? 3
      : 2;
}

function useColumnCount(): number {
  // 惰性取真实列数：SSR/首帧默认 4 仅作占位——列表分支只在客户端
  // 拿到数据后渲染，实际消费该值时 window 一定存在。
  const [cols, setCols] = useState(() =>
    typeof window === "undefined" ? 4 : computeCols(),
  );
  useEffect(() => {
    const queries = [
      window.matchMedia("(min-width: 1024px)"),
      window.matchMedia("(min-width: 768px)"),
    ];
    const onChange = () => setCols(computeCols());
    queries.forEach((q) => q.addEventListener("change", onChange));
    return () => queries.forEach((q) => q.removeEventListener("change", onChange));
  }, []);
  return cols;
}

/** JS 贪心最短列瀑布流：每张卡放进当前累计高度最矮的列，高度按
 *  高宽比累加（列等宽，h/w 即相对高度）。分配对前缀稳定——追加
 *  新页不会移动已渲染的卡；列数变化（跨断点）才整体重排。
 *  无限滚动：底部哨兵 + IntersectionObserver（rootMargin 600px），
 *  isFetchingNextPage 期间不重复触发。新页卡片 fade-in-up 40ms
 *  阶梯入场（reduced-motion 由 globals.css 全局关闭）。 */
export default function MasonryGrid({
  pages,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
}: MasonryGridProps) {
  const cols = useColumnCount();
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasNextPage) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !isFetchingNextPage) fetchNextPage();
      },
      { rootMargin: "600px 0px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // 阶梯延迟按页内序号计（每页重新从 0 数），封顶 6 档防长页拖沓。
  const items = pages.flatMap((page) =>
    page.map((post, j) => ({ post, delay: Math.min(j, 6) * 40 })),
  );
  const columns = Array.from({ length: cols }, () => [] as typeof items);
  const heights = new Array<number>(cols).fill(0);
  for (const it of items) {
    const k = heights.indexOf(Math.min(...heights));
    columns[k].push(it);
    heights[k] += it.post.height / it.post.width;
  }

  return (
    <>
      <div className="flex items-start gap-1.5">
        {columns.map((column, ci) => (
          <div key={ci} className="flex min-w-0 flex-1 flex-col gap-1.5">
            {column.map((it) => (
              <div
                key={it.post.id}
                className="animate-fade-in-up"
                style={{ animationDelay: `${it.delay}ms` }}
              >
                <PostCard post={it.post} />
              </div>
            ))}
          </div>
        ))}
      </div>
      {/* 分页加载指示：居中玻璃胶囊（设计稿"正在加载第 2 页…"）。 */}
      <div ref={sentinelRef} className="flex justify-center py-2" role="status">
        {isFetchingNextPage && (
          <span className="glass-bar rounded-pill px-5 py-2 text-[12.5px] text-muted">
            正在加载第 {pages.length + 1} 页…
          </span>
        )}
      </div>
    </>
  );
}
