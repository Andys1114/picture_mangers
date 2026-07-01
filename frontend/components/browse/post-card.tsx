"use client";

import { Star } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { toast } from "sonner";
import { mediaUrl } from "@/lib/api";
import { ratingColor } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type { PostSummary } from "@/lib/types";

interface PostCardProps {
  post: PostSummary;
}

/** A masonry tile. Hover surfaces a favorite ★ (local optimistic visual only —
 *  the favorites API lands in #8) and a rating color block (bottom-right).
 *  width/height are set explicitly to prevent layout shift (CLS). */
export function PostCard({ post }: PostCardProps) {
  const [fav, setFav] = useState(post.favorite);
  const rc = ratingColor(post.rating);

  const onFav = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setFav((v) => !v);
    toast(fav ? "已取消收藏（待 #8 接口）" : "已收藏（待 #8 接口）");
  };

  return (
    <article className="group relative mb-1 overflow-hidden rounded-md bg-surface">
      <Image
        src={mediaUrl(post.preview_path)}
        alt={`图片 ${post.id}`}
        width={post.width}
        height={post.height}
        loading="lazy"
        unoptimized
        className="w-full h-auto block"
      />
      {/* Hover overlay */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors pointer-events-none group-hover:pointer-events-auto" />
      <button
        type="button"
        onClick={onFav}
        aria-pressed={fav}
        aria-label={fav ? "取消收藏" : "收藏"}
        className={cn(
          "absolute top-2 right-2 h-9 w-9 rounded-full flex items-center justify-center backdrop-blur-sm transition-opacity opacity-0 group-hover:opacity-100 cursor-pointer focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
          fav ? "bg-safe/90 text-white" : "bg-black/50 text-white hover:bg-black/70",
        )}
      >
        <Star className="h-4 w-4" fill={fav ? "currentColor" : "none"} />
      </button>
      {/* Rating color block */}
      <span
        className={cn("absolute bottom-0 right-0 h-1.5 w-12", rc.bg)}
        aria-label={`分级：${post.rating}`}
        title={`分级：${post.rating}`}
      />
    </article>
  );
}
