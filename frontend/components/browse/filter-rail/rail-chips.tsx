"use client";

import { X } from "lucide-react";
import { ratingColor, ratingLabel, tagCategoryColor } from "@/lib/colors";
import { useTags } from "@/hooks/useTags";
import { useTagTree } from "@/hooks/useTagTree";
import { cn } from "@/lib/utils";
import type { TagCategory } from "@/lib/types";
import { useFilterParams } from "../use-filter-params";

const CHIP =
  "inline-flex shrink-0 cursor-pointer items-center gap-[5px] rounded-pill border px-[11px] py-1 font-mono text-xs font-medium transition duration-150 ease-out-soft hover:brightness-125 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

interface RailChipsProps {
  /** true = 容器用 display:contents，chips 直接成为外层 flex 行的子项
   *  （移动 chips 行横向滚动复用）；false = 自带 flex-wrap 布局（桌面 rail）。 */
  bare?: boolean;
}

/** 已选条件 chips 区：URL 里的标签 + 评级子集，逐个可删（点击即从 URL 移除）。
 *  标签分类色从标签索引 + 连带树缓存（与 rail-tags 同一份查询）反查，
 *  查不到按 general 展示。无选中时整块不渲染。 */
export default function RailChips({ bare = false }: RailChipsProps) {
  const { tags, ratings, removeTag, removeRating } = useFilterParams();
  const tagList = useTags({ order: "count" });
  const tree = useTagTree();

  if (tags.length === 0 && ratings.length === 0) return null;

  const categoryOf = new Map<string, TagCategory>();
  for (const t of tagList.data ?? []) categoryOf.set(t.name, t.category);
  for (const node of tree.data ?? []) {
    categoryOf.set(node.tag.name, node.tag.category);
    for (const c of node.consequents) categoryOf.set(c.name, c.category);
  }

  return (
    <div className={bare ? "contents" : "flex flex-wrap items-center gap-1.5"}>
      {tags.map((name) => (
        <button
          key={name}
          type="button"
          aria-label={`移除标签 ${name}`}
          onClick={() => removeTag(name)}
          className={cn(CHIP, tagCategoryColor(categoryOf.get(name) ?? "general"))}
        >
          {name}
          <X size={12} aria-hidden />
        </button>
      ))}
      {ratings.map((r) => (
        <button
          key={r}
          type="button"
          aria-label={`移除评级 ${ratingLabel(r)}`}
          onClick={() => removeRating(r)}
          className={cn(CHIP, ratingColor(r))}
        >
          {ratingLabel(r)}
          <X size={12} aria-hidden />
        </button>
      ))}
    </div>
  );
}
