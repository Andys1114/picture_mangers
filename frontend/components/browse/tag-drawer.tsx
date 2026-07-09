"use client";

import { Tags } from "lucide-react";
import { useState } from "react";
import { Sheet } from "@/components/ui/sheet";

/** Tag drawer shell. The tag tree data depends on GET /api/tags (subtask #7),
 *  so this milestone shows an empty state. The shell wires the slide-out + Esc. */
export function TagDrawer() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="打开标签筛选"
        className="inline-flex items-center gap-1.5 h-10 px-3 rounded-md text-sm font-medium text-foreground hover:bg-surface cursor-pointer transition duration-150 ease-out-soft active:scale-[0.97] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
      >
        <Tags className="h-4 w-4" aria-hidden />
        <span className="hidden sm:inline">标签</span>
      </button>
      <Sheet open={open} onOpenChange={setOpen} aria-label="标签筛选">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h2 className="font-medium">标签筛选</h2>
        </div>
        <p className="p-4 text-sm text-muted leading-relaxed">
          标签筛选即将上线：届时这里会按分类展示热门标签。
        </p>
      </Sheet>
    </>
  );
}
