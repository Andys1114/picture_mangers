"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useState } from "react";
import { mediaUrl } from "@/lib/api";
import { ratingIcon, ratingLabel, ratingTextColor } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type { PostSummary } from "@/lib/types";

interface PostCardProps {
  post: PostSummary;
}

/** 悬停浮层元素共用的淡入淡出（键盘聚焦同样显示，a11y 对等）。 */
const HOVER_REVEAL =
  "opacity-0 transition-opacity duration-150 ease-out-soft group-hover:opacity-100 group-focus-within:opacity-100";

/** 瀑布流卡片（radius 14）：点击 push `?photoId=`（保留现有筛选参数，
 *  灯箱在 D5 消费该参数；URL 语义见 CONTEXT.md"详情页"）。
 *  悬停/聚焦态：底部黑渐变浮层 + 评级 chip（黑底 90% 保证 AA 对比，
 *  色/图标/文案三者同时传达评级）+ mono id。图片 lazy 加载，
 *  width/height 显式声明 → 浏览器按宽高比预留占位，不跳动；
 *  加载完成前盖 shimmer，完成后淡入。无星标（父任务决策 3）。 */
export default function PostCard({ post }: PostCardProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [loaded, setLoaded] = useState(false);
  const RatingIcon = ratingIcon(post.rating);
  const idLabel = `#${String(post.id).padStart(4, "0")}`;

  const params = new URLSearchParams(searchParams.toString());
  params.set("photoId", String(post.id));

  return (
    <Link
      href={`${pathname}?${params.toString()}`}
      scroll={false}
      className="group relative block overflow-hidden rounded-card bg-surface transition-shadow duration-150 ease-out-soft hover:shadow-e2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Image
        src={mediaUrl(post.preview_path)}
        alt={`插画 ${idLabel}`}
        width={post.width}
        height={post.height}
        loading="lazy"
        unoptimized
        onLoad={() => setLoaded(true)}
        className={cn(
          "block h-auto w-full transition-opacity duration-300 ease-out-soft",
          loaded ? "opacity-100" : "opacity-0",
        )}
      />
      {!loaded && <span aria-hidden className="shimmer absolute inset-0 block" />}

      {/* 底部黑渐变浮层（设计稿：0.68 → 透明 @46%），文字浮层的暗部保障。 */}
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-x-0 bottom-0 block h-[46%] bg-gradient-to-t from-black/70 to-transparent",
          HOVER_REVEAL,
        )}
      />
      <span
        className={cn(
          "pointer-events-none absolute bottom-2.5 left-2.5 inline-flex items-center gap-[5px] rounded-pill bg-black/90 px-[11px] py-1 font-mono text-[11px] font-semibold backdrop-blur",
          ratingTextColor(post.rating),
          HOVER_REVEAL,
        )}
      >
        <RatingIcon size={13} aria-hidden />
        {ratingLabel(post.rating)}
      </span>
      <span
        className={cn(
          "pointer-events-none absolute bottom-2.5 right-2.5 font-mono text-[11px] text-white/85",
          HOVER_REVEAL,
        )}
      >
        {idLabel}
      </span>
    </Link>
  );
}
