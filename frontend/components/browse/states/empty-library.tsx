import { CloudDownload, FolderOpen, Images } from "lucide-react";
import { Button } from "@/components/ui/button";

/** 空图库（无任何筛选且 total=0）：文案沿用现有版本；两个导入 CTA
 *  先给禁用态 + "管理面板即将上线"说明——管理页是后续子任务，
 *  不能出现死链。 */
export default function EmptyLibrary() {
  return (
    <div className="flex flex-col items-center justify-center gap-3.5 py-28 text-center">
      <span className="flex h-[72px] w-[72px] items-center justify-center rounded-pill border border-accent-soft-edge bg-grad-accent-soft">
        <Images size={32} className="text-accent-soft-fg" aria-hidden />
      </span>
      <p className="text-[17px] font-bold">这里还没有图片</p>
      <p className="text-[13px] leading-[1.8] text-muted">
        导入本地文件夹或抓取 Danbooru 后，
        <br />
        图片会出现在这里。
      </p>
      <div className="mt-1.5 flex gap-2.5">
        <Button disabled title="管理面板即将上线">
          <FolderOpen size={16} aria-hidden />
          导入本地文件夹
        </Button>
        <Button variant="outline" disabled title="管理面板即将上线">
          <CloudDownload size={16} aria-hidden />
          抓取 Danbooru
        </Button>
      </div>
      <p className="text-[11px] text-faint">管理面板即将上线，届时可从这里导入图片</p>
    </div>
  );
}
