"use client";

import { useCallback, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { Rating } from "@/lib/types";

export const ALL_RATINGS: readonly Rating[] = ["safe", "questionable", "explicit"];

function isRating(v: string): v is Rating {
  return (ALL_RATINGS as readonly string[]).includes(v);
}

/** 浏览筛选的 URL 状态（唯一事实源，state-management）：
 *  - `?tags=a+b` 空格分隔，AND 语义；
 *  - `?ratings=safe,questionable` 逗号多选，全选/空 = 不带参数。
 *  写操作一律 router.replace（不产生历史堆叠），并保留其余查询参数
 *  （如后续的 ?photoId=）。 */
export function useFilterParams() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  /** 已选标签名列表（来自 ?tags=，可能为空）。 */
  const tags = useMemo(
    () => (searchParams.get("tags") ?? "").split(/\s+/).filter(Boolean),
    [searchParams],
  );

  /** URL 里显式出现的评级子集（空数组 = 不带参数 = 全部评级）。 */
  const ratings = useMemo(
    () => (searchParams.get("ratings") ?? "").split(",").filter(isRating),
    [searchParams],
  );

  /** 勾选态视图：不带参数时三项全选。 */
  const checkedRatings = ratings.length > 0 ? ratings : [...ALL_RATINGS];

  const write = useCallback(
    (nextTags: string[], nextRatings: Rating[]) => {
      const params = new URLSearchParams(searchParams.toString());
      if (nextTags.length > 0) params.set("tags", nextTags.join(" "));
      else params.delete("tags");
      // 按固定顺序去重序列化；全选或清空都回到"不带参数"。
      const subset = ALL_RATINGS.filter((r) => nextRatings.includes(r));
      if (subset.length > 0 && subset.length < ALL_RATINGS.length) {
        params.set("ratings", subset.join(","));
      } else {
        params.delete("ratings");
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  /** 整体替换标签集（搜索框回车提交）。 */
  const setTags = useCallback(
    (next: string[]) => write(next, ratings),
    [write, ratings],
  );

  /** 单个标签切换选中（筛选栏 chip 点击）。 */
  const toggleTag = useCallback(
    (name: string) =>
      write(
        tags.includes(name) ? tags.filter((t) => t !== name) : [...tags, name],
        ratings,
      ),
    [write, tags, ratings],
  );

  const removeTag = useCallback(
    (name: string) => write(tags.filter((t) => t !== name), ratings),
    [write, tags, ratings],
  );

  const toggleRating = useCallback(
    (r: Rating) => {
      const current = ratings.length > 0 ? ratings : [...ALL_RATINGS];
      write(
        tags,
        current.includes(r) ? current.filter((x) => x !== r) : [...current, r],
      );
    },
    [write, tags, ratings],
  );

  /** 从显式子集里去掉一个评级（已选条件 chip 删除）。 */
  const removeRating = useCallback(
    (r: Rating) => write(tags, ratings.filter((x) => x !== r)),
    [write, tags, ratings],
  );

  /** 清空全部筛选（无结果态"清空全部筛选"chip）。 */
  const clearAll = useCallback(() => write([], []), [write]);

  return {
    tags,
    ratings,
    checkedRatings,
    /** useInfinitePosts 入参（wire 格式；空 = 不传）。 */
    tagsParam: tags.length > 0 ? tags.join(" ") : undefined,
    ratingsParam: ratings.length > 0 ? ratings.join(",") : undefined,
    setTags,
    toggleTag,
    removeTag,
    toggleRating,
    removeRating,
    clearAll,
  };
}
