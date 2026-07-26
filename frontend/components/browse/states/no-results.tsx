"use client";

import { SearchX, X } from "lucide-react";
import { ratingColor, ratingLabel, tagCategoryColor } from "@/lib/colors";
import { useTags } from "@/hooks/useTags";
import { useTagTree } from "@/hooks/useTagTree";
import { cn } from "@/lib/utils";
import type { TagCategory } from "@/lib/types";
import { useFilterParams } from "../use-filter-params";

const CHIP =
  "inline-flex cursor-pointer items-center gap-[5px] rounded-pill border px-3.5 py-[7px] text-xs font-medium transition duration-150 ease-out-soft hover:brightness-125 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** 筛选无结果（有筛选且 total=0）：逐项放宽建议——把当前每个筛选
 *  条件渲染成可点 chip，点击即从 URL 移除该条件（use-filter-params
 *  的 remove 方法），另给"清空全部筛选"。分类色反查沿用 rail-chips
 *  的做法（标签索引 + 连带树缓存，查不到按 general）。 */
export default function NoResults() {
  const { tags, ratings, removeTag, removeRating, clearAll } = useFilterParams();
  const tagList = useTags({ order: "count" });
  const tree = useTagTree();

  const categoryOf = new Map<string, TagCategory>();
  for (const t of tagList.data ?? []) categoryOf.set(t.name, t.category);
  for (const node of tree.data ?? []) {
    categoryOf.set(node.tag.name, node.tag.category);
    for (const c of node.consequents) categoryOf.set(c.name, c.category);
  }

  const summary = [...tags, ...ratings.map(ratingLabel)].join(" + ");

  return (
    <div className="flex flex-col items-center justify-center gap-3.5 py-28 text-center">
      <span className="flex h-[72px] w-[72px] items-center justify-center rounded-pill border border-strong bg-fill-2">
        <SearchX size={32} className="text-muted" aria-hidden />
      </span>
      <p className="text-[17px] font-bold">没有符合条件的图片</p>
      <p className="text-[13px] leading-[1.8] text-muted">
        当前条件：{summary}
        <br />
        试试放宽其中一项：
      </p>
      <div className="mt-1.5 flex max-w-xl flex-wrap justify-center gap-2">
        {tags.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => removeTag(name)}
            className={cn(CHIP, "bg-transparent", tagCategoryColor(categoryOf.get(name) ?? "general"))}
          >
            <X size={14} aria-hidden />
            移除 {name}
          </button>
        ))}
        {ratings.map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => removeRating(r)}
            className={cn(CHIP, "bg-transparent", ratingColor(r))}
          >
            <X size={14} aria-hidden />
            移除 {ratingLabel(r)}
          </button>
        ))}
        <button
          type="button"
          onClick={clearAll}
          className={cn(CHIP, "border-transparent bg-fill-3 text-primary")}
        >
          清空全部筛选
        </button>
      </div>
    </div>
  );
}
