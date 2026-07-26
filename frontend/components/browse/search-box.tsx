"use client";

import { useEffect, useRef } from "react";
import { Search } from "lucide-react";
import { useFilterParams } from "./use-filter-params";

/** 顶栏搜索胶囊：纯输入，无联想下拉（联想是子任务 2）。
 *  - 回车把输入按空格切词，整体替换进 `?tags=`（空格 = AND）；
 *  - 全局按 `/`（焦点不在输入框时）聚焦本框；
 *  - URL 是唯一事实源：外部改动（筛选栏 chip）通过 key 重挂输入框回填。 */
export default function SearchBox() {
  const inputRef = useRef<HTMLInputElement>(null);
  const { tags, setTags } = useFilterParams();
  const urlValue = tags.join(" ");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      const el = e.target as HTMLElement | null;
      if (
        el &&
        (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable)
      ) {
        return;
      }
      e.preventDefault();
      inputRef.current?.focus();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  return (
    <form
      role="search"
      className="mx-2 flex h-[38px] min-w-0 flex-1 items-center gap-[9px] rounded-pill border bg-fill-2 pl-[15px] pr-2 text-muted transition duration-150 ease-out-soft focus-within:border-ring focus-within:shadow-focus-ring"
      onSubmit={(e) => {
        e.preventDefault();
        setTags((inputRef.current?.value ?? "").split(/\s+/).filter(Boolean));
      }}
    >
      <Search size={18} aria-hidden className="shrink-0" />
      <input
        key={urlValue}
        ref={inputRef}
        type="text"
        defaultValue={urlValue}
        aria-label="搜索标签"
        placeholder="搜索标签，空格 = 同时满足…"
        autoComplete="off"
        spellCheck={false}
        className="min-w-0 flex-1 bg-transparent text-[13px] text-primary placeholder:text-muted focus:outline-none"
      />
      <kbd
        aria-hidden
        className="shrink-0 rounded-md bg-fill-3 px-2 py-[3px] font-mono text-[11px] font-semibold text-muted"
      >
        /
      </kbd>
    </form>
  );
}
