"use client";

import { Star } from "lucide-react";
import Image from "next/image";
import { useState } from "react";
import { toast } from "sonner";
import { mediaUrl } from "@/lib/api";
import { ratingColor, ratingIcon, ratingLabel } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type { PostSummary } from "@/lib/types";

interface PostCardProps {
  post: PostSummary;
}

/** A masonry tile. Hover (or focus) surfaces a favorite ★ and a rating chip
 *  over a bottom gradient; the image fades in on load to avoid a flash of
 *  empty surface. width/height are set explicitly to prevent layout shift.
 *  The favorite ★ is local optimistic visual only — the favorites API lands
 *  in #8. */
export function PostCard({ post }: PostCardProps) {
  const [fav, setFav] = useState(post.favorite);
  const [loaded, setLoaded] = useState(false);
  const rc = ratingColor(post.rating);
  const RatingIcon = ratingIcon(post.rating);

  const onFav = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setFav((v) => !v);
    toast(fav ? "已取消收藏" : "已收藏（云端同步开发中）");
  };

  return (
    <article className="group relative mb-1 overflow-hidden rounded-lg bg-surface shadow-e1 transition-transform duration-200 ease-out-soft hover:scale-[1.02] hover:shadow-e2 hover:z-10">
      <Image
        src={mediaUrl(post.preview_path)}
        alt={`插画 ${post.id} · 分级 ${ratingLabel(post.rating)}`}
        width={post.width}
        height={post.height}
        loading="lazy"
        unoptimized
        onLoad={() => setLoaded(true)}
        className={cn(
          "w-full h-auto block transition-opacity duration-300 ease-out-soft",
          loaded ? "opacity-100" : "opacity-0",
        )}
      />
      {!loaded && (
        <div className="absolute inset-0 shimmer" aria-hidden />
      )}

      {/* Bottom gradient overlay — replaces a flat black wash. */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/70 to-transparent opacity-0 transition-opacity duration-200 ease-out-soft group-hover:opacity-100 group-focus-within:opacity-100" />

      {/* Rating chip: color + icon + label (not color alone). */}
      <span
        className={cn(
          "absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-full border border-white/10 px-2 py-0.5 text-xs font-medium opacity-0 transition-opacity duration-200 ease-out-soft group-hover:opacity-100 group-focus-within:opacity-100",
          "bg-black/90 backdrop-blur-sm",
          rc.text,
        )}
        title={`分级：${post.rating}`}
      >
        <RatingIcon className="h-3 w-3" aria-hidden />
        {ratingLabel(post.rating)}
      </span>

      {/* Favorite ★ — visible on hover/focus and on touch (card-fav). */}
      <button
        type="button"
        onClick={onFav}
        aria-pressed={fav}
        aria-label={fav ? "取消收藏" : "收藏"}
        className={cn(
          "card-fav absolute top-2 right-2 h-9 w-9 rounded-full flex items-center justify-center backdrop-blur-sm cursor-pointer transition-[opacity,background-color,transform] duration-200 ease-out-soft active:scale-[0.97] opacity-0 group-hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
          fav
            ? "bg-safe/90 text-white opacity-100"
            : "bg-black/50 text-white hover:bg-black/70",
        )}
      >
        <Star className="h-4 w-4" fill={fav ? "currentColor" : "none"} aria-hidden />
      </button>
    </article>
  );
}
