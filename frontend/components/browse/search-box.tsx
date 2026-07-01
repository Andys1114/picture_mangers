"use client";

import { Search } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/** Basic search box: submits to ?tags=<query> (URL state, shareable).
 *  Chip-coloring + autocomplete land in subtask #7. */
export function SearchBox({ className }: { className?: string }) {
  const router = useRouter();
  const params = useSearchParams();
  const [value, setValue] = useState(params.get("tags") ?? "");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = value.trim();
    const next = new URLSearchParams(params.toString());
    if (q) next.set("tags", q);
    else next.delete("tags");
    router.replace(q ? `/?${next.toString()}` : "/");
  };

  return (
    <form onSubmit={submit} className={cn("relative flex-1 max-w-md", className)} role="search">
      <Search
        className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted"
        aria-hidden
      />
      <Input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="搜索标签（空格分隔，AND）"
        aria-label="搜索标签"
        className="pl-9"
      />
    </form>
  );
}
