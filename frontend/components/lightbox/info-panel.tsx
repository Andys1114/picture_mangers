"use client";

import Image from "next/image";
import { Download, ExternalLink, X } from "lucide-react";
import { useMemo } from "react";
import { useSwipe } from "./use-swipe";
import { useArtistPosts } from "@/hooks/useArtistPosts";
import { useTagTree } from "@/hooks/useTagTree";
import { mediaUrl } from "@/lib/api";
import { ratingColor, ratingIcon, ratingLabel, tagCategoryColor } from "@/lib/colors";
import { cn } from "@/lib/utils";
import type { PostDetail, Tag } from "@/lib/types";

/** 区块小标题（mono 10px 字距 1.5px，同筛选栏）。 */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="font-mono text-[10px] font-semibold uppercase tracking-[1.5px] text-label">
      {children}
    </h3>
  );
}

interface TagChipProps {
  tag: Tag;
  onClick: () => void;
}

/** 详情标签 chip：分类三件套配色 + 计数；点击 = 关灯箱并按该标签筛选。 */
function TagChip({ tag, onClick }: TagChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex cursor-pointer items-center gap-1.5 rounded-pill border px-3 py-[3px] font-mono text-xs font-medium transition duration-150 ease-out-soft hover:brightness-125 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        tagCategoryColor(tag.category),
      )}
    >
      {tag.name}
      <span className="text-[11px] opacity-60">{tag.post_count}</span>
    </button>
  );
}

interface ArtistSectionProps {
  artists: Tag[];
  currentId: number;
  onGoto: (id: number) => void;
  onFilterTag: (name: string) => void;
}

/** 作者区：琥珀 chip + "该作者更多"4 张 44px 缩略图 + "+N"。
 *  缩略图数据按首个作者标签单独取一小页，剔除当前图后凑 4 格。 */
function ArtistSection({ artists, currentId, onGoto, onFilterTag }: ArtistSectionProps) {
  const preview = useArtistPosts(artists[0].name);
  const total = preview.data?.meta.total ?? artists[0].post_count;
  const others = (preview.data?.data ?? []).filter((p) => p.id !== currentId).slice(0, 4);
  const rest = Math.max(total - 1 - others.length, 0);

  return (
    <div className="flex flex-col gap-2.5">
      <SectionLabel>作者 ARTIST</SectionLabel>
      <div className="flex flex-wrap items-center gap-1.5">
        {artists.map((tag) => (
          <TagChip key={tag.id} tag={tag} onClick={() => onFilterTag(tag.name)} />
        ))}
        {others.length > 0 && (
          <span className="text-[10.5px] text-muted">该作者更多 →</span>
        )}
      </div>
      {others.length > 0 && (
        <div className="flex gap-1.5">
          {others.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => onGoto(p.id)}
              aria-label={`查看 ${artists[0].name} 作品 #${p.id}`}
              className="cursor-pointer overflow-hidden rounded-thumb transition duration-150 ease-out-soft hover:brightness-125 active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <Image
                src={mediaUrl(p.preview_path)}
                alt=""
                width={88}
                height={88}
                unoptimized
                className="h-11 w-11 object-cover"
              />
            </button>
          ))}
          {rest > 0 && (
            <span className="flex h-11 w-11 items-center justify-center rounded-thumb bg-fill-1 font-mono text-[10px] font-medium text-muted">
              +{rest}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/** 元数据 mono 行：左标签弱色，右值次级色。 */
function MetaRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex font-mono text-[11px] text-muted">
      {label}
      <span className="ml-auto text-right text-secondary">{children}</span>
    </div>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
}

interface InfoPanelProps {
  detail: PostDetail;
  /** 直达打开（无列表上下文，禁翻页）：键位/手势提示只保留关闭。 */
  direct: boolean;
  onClose: () => void;
  onGoto: (id: number) => void;
  onFilterTag: (name: string) => void;
  /** <768 信息半层两档：false = 收起只露标题行；true = 展开成滚动面板。 */
  mobileExpanded: boolean;
  onMobileExpandedChange: (expanded: boolean) => void;
}

/** 灯箱信息浮层：标题行 / 下载·原图操作 / 作者区 / 标签连带成组 / GENERAL /
 *  元数据 mono 行 / 底部键位提示。无星标、无差分区（后续子任务）。
 *  桌面（md+）= 左侧 320px 全高玻璃卡（radius 20）。
 *  移动（<768）= 底部半层（24px 顶角）：受控 max-height 两档切换——收起只露
 *  拖动把手 + 标题行，展开成可滚动面板；把手点按或标题区上拉/下拉切换。 */
export default function InfoPanel({
  detail,
  direct,
  onClose,
  onGoto,
  onFilterTag,
  mobileExpanded,
  onMobileExpandedChange,
}: InfoPanelProps) {
  const tree = useTagTree();
  // 标题区手势：上拉展开 / 下拉收起（阈值与图区同一套 use-swipe）。
  const headerSwipe = useSwipe({
    onSwipeUp: () => onMobileExpandedChange(true),
    onSwipeDown: () => onMobileExpandedChange(false),
  });
  const RatingIcon = ratingIcon(detail.rating);
  const idLabel = `#${String(detail.id).padStart(4, "0")}`;
  const originalUrl = mediaUrl(detail.file_path);
  const ext = detail.file_path.split(".").pop()?.toUpperCase() ?? "";

  const artists = detail.tags.filter((t) => t.category === "artist");
  const generals = detail.tags.filter((t) => t.category === "general");

  // 标签区（非 general / 非 artist）连带成组：与筛选栏同款——图上标签里
  // 作为母标签（consequent）出现的升为分组行，其子标签紫线缩进其下。
  const { groups, flat } = useMemo(() => {
    const pool = detail.tags.filter(
      (t) => t.category !== "general" && t.category !== "artist",
    );
    const inPool = new Set(pool.map((t) => t.id));
    const byParent = new Map<number, { parent: Tag; children: Tag[] }>();
    const grouped = new Set<number>();
    for (const node of tree.data ?? []) {
      if (!inPool.has(node.tag.id)) continue;
      for (const parent of node.consequents) {
        if (!inPool.has(parent.id)) continue;
        const group = byParent.get(parent.id) ?? { parent, children: [] };
        group.children.push(node.tag);
        byParent.set(parent.id, group);
        grouped.add(parent.id);
        grouped.add(node.tag.id);
      }
    }
    return {
      groups: [...byParent.values()],
      flat: pool.filter((t) => !grouped.has(t.id)),
    };
  }, [detail.tags, tree.data]);

  const actionClass =
    "flex h-[38px] flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-pill border border-border-pop bg-fill-2 text-[13px] font-medium text-secondary transition duration-150 ease-out-soft hover:bg-fill-3 hover:text-primary active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <aside
      className={cn(
        "glass-pop absolute flex flex-col gap-3",
        // 桌面：左侧 320px 全高浮层，整卡滚动
        "md:bottom-7 md:left-7 md:top-7 md:w-[320px] md:overflow-y-auto md:rounded-panel md:p-5",
        // 移动：底部半层（顶角 24），受控 max-height 两档 + 220ms 过渡
        "max-md:inset-x-0 max-md:bottom-0 max-md:rounded-t-modal max-md:border-b-0 max-md:px-4 max-md:pb-[max(18px,env(safe-area-inset-bottom))] max-md:pt-0 max-md:transition-[max-height] max-md:duration-220 max-md:ease-out-soft",
        mobileExpanded
          ? "max-md:max-h-[62dvh] max-md:overflow-y-auto"
          : "max-md:max-h-[76px] max-md:overflow-hidden",
      )}
    >
      {/* 标题区（把手 + 标题行）：<768 整块可上拉/下拉切换两档 */}
      <div
        className="flex shrink-0 flex-col gap-3 max-md:touch-none"
        {...headerSwipe}
      >
        <button
          type="button"
          onClick={() => onMobileExpandedChange(!mobileExpanded)}
          aria-expanded={mobileExpanded}
          aria-label="信息面板"
          className="-mb-2 mx-auto flex h-6 w-16 shrink-0 cursor-pointer items-center justify-center rounded-pill transition duration-150 ease-out-soft hover:bg-fill-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
        >
          <span aria-hidden className="h-1 w-10 rounded-pill bg-fill-3" />
        </button>
        {/* 标题行：mono id + 评级 chip + 关闭钮（<768 由顶部返回钮代劳） */}
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-sm font-semibold">{idLabel}</span>
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-pill border px-2.5 py-[3px] font-mono text-[11px] font-semibold",
              ratingColor(detail.rating),
            )}
          >
            <RatingIcon size={12} aria-hidden />
            {ratingLabel(detail.rating)}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="关闭"
            className="ml-auto flex h-[30px] w-[30px] cursor-pointer items-center justify-center rounded-pill bg-fill-2 text-secondary transition duration-150 ease-out-soft hover:bg-fill-3 hover:text-primary active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-md:hidden"
          >
            <X size={16} aria-hidden />
          </button>
        </div>
      </div>

      {/* 内容区：<768 收起时被 overflow 裁掉；键盘焦点进入即自动展开
          （隐藏内容不可见但仍在 Tab 序，需要焦点视差补偿）。 */}
      <div
        className="flex min-h-0 flex-1 flex-col gap-3"
        onFocusCapture={() => {
          if (!mobileExpanded) onMobileExpandedChange(true);
        }}
      >
        {/* 操作行：下载原图文件 / 新标签打开原图 */}
        <div className="flex gap-2">
          <a href={originalUrl} download className={actionClass}>
            <Download size={16} aria-hidden />
            下载
          </a>
          <a
            href={originalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={actionClass}
          >
            <ExternalLink size={16} aria-hidden />
            原图
          </a>
        </div>

        <div aria-hidden className="h-px shrink-0 bg-divider" />

        {artists.length > 0 && (
          <ArtistSection
            artists={artists}
            currentId={detail.id}
            onGoto={onGoto}
            onFilterTag={onFilterTag}
          />
        )}

        {(groups.length > 0 || flat.length > 0) && (
          <div className="flex flex-col gap-2.5">
            <SectionLabel>标签 · 连带成组</SectionLabel>
            {groups.length > 0 && (
              <div className="flex flex-col gap-[7px] rounded-thumb-lg border bg-fill-1 p-2">
                {groups.map((group) => (
                  <div key={group.parent.id} className="flex flex-col gap-[7px]">
                    <div className="flex items-center gap-[7px]">
                      <TagChip
                        tag={group.parent}
                        onClick={() => onFilterTag(group.parent.name)}
                      />
                      <span className="font-mono text-[10px] text-faint">母标签</span>
                    </div>
                    <div className="ml-2 flex flex-wrap gap-[5px] border-l-2 border-accent-soft-edge pl-[9px]">
                      {group.children.map((child) => (
                        <TagChip
                          key={child.id}
                          tag={child}
                          onClick={() => onFilterTag(child.name)}
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
                  <TagChip key={tag.id} tag={tag} onClick={() => onFilterTag(tag.name)} />
                ))}
              </div>
            )}
          </div>
        )}

        {generals.length > 0 && (
          <div className="flex flex-col gap-2.5">
            <SectionLabel>General</SectionLabel>
            <div className="flex flex-wrap gap-1.5">
              {generals.map((tag) => (
                <TagChip key={tag.id} tag={tag} onClick={() => onFilterTag(tag.name)} />
              ))}
            </div>
          </div>
        )}

        <div aria-hidden className="h-px shrink-0 bg-divider" />

        <div className="flex flex-col gap-[7px]">
          <MetaRow label="尺寸">
            {detail.width} × {detail.height}
            {ext && ` · ${ext}`}
          </MetaRow>
          <MetaRow label="入库">{formatDate(detail.created_at)}</MetaRow>
          <MetaRow label="来源">
            {detail.source_url ? (
              <a
                href={detail.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline decoration-strong underline-offset-2 transition duration-150 ease-out-soft hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {detail.source_site ?? "查看来源"}
              </a>
            ) : (
              "本地导入"
            )}
          </MetaRow>
          <MetaRow label="md5">
            <span title={detail.md5}>
              {detail.md5.slice(0, 4)}…{detail.md5.slice(-4)}
            </span>
          </MetaRow>
        </div>

        <p className="mt-auto pt-1 text-center text-[11px] text-faint max-md:hidden">
          {direct ? "Esc 关闭" : "← → 翻页 · Esc 关闭"}
        </p>
        <p className="pt-1 text-center text-[11px] text-faint md:hidden">
          {direct ? "下滑关闭" : "左右滑动切换 · 下滑关闭"}
        </p>
      </div>
    </aside>
  );
}
