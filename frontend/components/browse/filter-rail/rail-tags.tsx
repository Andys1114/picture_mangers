"use client";

import { useMemo } from "react";
import { useTags } from "@/hooks/useTags";
import { useTagTree } from "@/hooks/useTagTree";
import { Skeleton } from "@/components/ui/skeleton";
import { tagCategoryColor } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type { Tag } from "@/lib/types";
import { useFilterParams } from "../use-filter-params";

/** 平铺区最多展示的标签数（按 post_count 降序取前 N）。 */
const RAIL_TAG_LIMIT = 30;

interface TagChipProps {
  tag: Tag;
  active: boolean;
  onToggle: () => void;
  /** 平铺普通 chip 时带计数；成组区不带（对齐设计稿）。 */
  showCount?: boolean;
}

/** 可点选标签 chip：分类三件套配色；选中时边框提到当前文字色 + aria-pressed。 */
function TagChip({ tag, active, onToggle, showCount = false }: TagChipProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onToggle}
      className={cn(
        "inline-flex cursor-pointer items-center gap-1 rounded-pill border px-2.5 py-[3px] font-mono text-[11.5px] font-medium transition duration-150 ease-out-soft hover:brightness-125 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        tagCategoryColor(tag.category),
        active && "border-current",
      )}
    >
      {tag.name}
      {showCount && (
        <span className="text-[10px] opacity-70">{tag.post_count}</span>
      )}
    </button>
  );
}

/** 标签区：列出可筛选的标签本身（listTags 按 post_count 降序前 N）。
 *  连带树用来"升组"：作为母标签（consequent）出现的标签成为分组行，
 *  其 antecedents 以左侧 2px 紫线缩进其下；进了组的标签不再重复平铺。
 *  点击任一 chip = 在 ?tags= 里切换选中。 */
export default function RailTags() {
  const tagsQuery = useTags({ order: "count" });
  const tree = useTagTree();
  const { tags: selected, toggleTag } = useFilterParams();

  const { groups, flat } = useMemo(() => {
    const top = (tagsQuery.data ?? []).slice(0, RAIL_TAG_LIMIT);
    // 后端 tree 的方向是"子标签 → 其直接母标签"，按母标签分组倒排。
    const byParent = new Map<number, { parent: Tag; children: Tag[] }>();
    const grouped = new Set<number>();
    for (const node of tree.data ?? []) {
      for (const parent of node.consequents) {
        const group = byParent.get(parent.id) ?? { parent, children: [] };
        group.children.push(node.tag);
        byParent.set(parent.id, group);
        grouped.add(parent.id);
        grouped.add(node.tag.id);
      }
    }
    return {
      groups: [...byParent.values()],
      flat: top.filter((t) => !grouped.has(t.id)),
    };
  }, [tagsQuery.data, tree.data]);

  return (
    <div className="flex flex-col gap-2">
      <h3 className="font-mono text-[10px] font-semibold uppercase tracking-[1.5px] text-label">
        标签 TAGS
      </h3>
      {tagsQuery.isLoading || tree.isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-7 w-full rounded-thumb-lg" />
          <Skeleton className="h-7 w-3/4 rounded-thumb-lg" />
        </div>
      ) : tagsQuery.isError ? (
        <p className="text-[11.5px] text-faint">标签加载失败，请稍后重试</p>
      ) : flat.length === 0 && groups.length === 0 ? (
        <p className="text-[11.5px] text-faint">还没有标签</p>
      ) : (
        <>
          {groups.length > 0 && (
            <div className="flex flex-col gap-[7px] rounded-thumb-lg border bg-fill-1 p-2">
              {groups.map((group) => (
                <div key={group.parent.id} className="flex flex-col gap-[7px]">
                  <div className="flex items-center gap-[7px]">
                    <TagChip
                      tag={group.parent}
                      active={selected.includes(group.parent.name)}
                      onToggle={() => toggleTag(group.parent.name)}
                    />
                    <span className="font-mono text-[10px] text-faint">母标签</span>
                  </div>
                  <div className="ml-2 flex flex-wrap gap-[5px] border-l-2 border-accent-soft-edge pl-[9px]">
                    {group.children.map((child) => (
                      <TagChip
                        key={child.id}
                        tag={child}
                        active={selected.includes(child.name)}
                        onToggle={() => toggleTag(child.name)}
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          {flat.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {flat.map((tag) => (
                <TagChip
                  key={tag.id}
                  tag={tag}
                  active={selected.includes(tag.name)}
                  onToggle={() => toggleTag(tag.name)}
                  showCount
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
