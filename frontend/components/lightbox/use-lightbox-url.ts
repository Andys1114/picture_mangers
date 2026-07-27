"use client";

import { useCallback, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** 灯箱的 URL 状态（?photoId=，语义见 CONTEXT.md"详情页"）：
 *  - 打开 = push（会话内点图，post-card 的 Link 已做，这里的 open 供缩略图等场景）；
 *  - ←→ 翻页 = replace（不产生后退地狱）；
 *  - 关闭 = 会话内打开走 history.back()；刷新/直达（挂载时参数已在）
 *    back 会离站，改为 replace 掉 photoId 参数；
 *  - 直达（`direct`）= 无列表上下文，调用方须禁用 ←→ 翻页（prd R3）。
 *  所有写操作保留其余查询参数（?tags=、?ratings=）。
 *  注意：会话内/直达的判定依赖跨开合观察 photoId 从无到有的转变，
 *  本 hook 必须由常驻组件（Lightbox 外壳）持有，浮层内新挂实例会恒判直达。 */
export function useLightboxUrl() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const raw = searchParams.get("photoId");
  const parsed = raw === null ? Number.NaN : Number(raw);
  const photoId = Number.isInteger(parsed) && parsed > 0 ? parsed : null;

  // 会话内打开判定：观察到 photoId 从无到有（= 本页挂载期间被 push 进来）；
  // 挂载首帧参数已存在 = 刷新/直达。render 期派生（React"渲染中修正状态"
  // 模式，比 useEffect 早一帧提交），翻页钮不会先渲染一帧再消失。
  const [track, setTrack] = useState({ id: photoId, inSession: false });
  const inSession =
    photoId === null ? false : track.id === null ? true : track.inSession;
  if (track.id !== photoId || track.inSession !== inSession) {
    setTrack({ id: photoId, inSession });
  }
  /** 直达/刷新打开的灯箱（无列表上下文）：禁翻页、关闭走 replace。 */
  const direct = photoId !== null && !inSession;

  const buildUrl = useCallback(
    (mutate: (p: URLSearchParams) => void) => {
      const params = new URLSearchParams(searchParams.toString());
      mutate(params);
      const qs = params.toString();
      return qs ? `${pathname}?${qs}` : pathname;
    },
    [pathname, searchParams],
  );

  /** 会话内打开（push）：作者缩略图之外的入口备用。 */
  const open = useCallback(
    (id: number) =>
      router.push(buildUrl((p) => p.set("photoId", String(id))), { scroll: false }),
    [router, buildUrl],
  );

  /** 翻页 / 跳转同层图（replace，不叠历史）。 */
  const goto = useCallback(
    (id: number) =>
      router.replace(buildUrl((p) => p.set("photoId", String(id))), { scroll: false }),
    [router, buildUrl],
  );

  const close = useCallback(() => {
    if (inSession) router.back();
    else router.replace(buildUrl((p) => p.delete("photoId")), { scroll: false });
  }, [router, buildUrl, inSession]);

  /** 点标签跳筛选：关灯箱并把 ?tags= 置为该标签。用 replace 而非 push——
   *  若在直达的灯箱上 push 筛选页，浏览器后退会重开灯箱并让"会话内打开"
   *  误判成立，此时再关闭走 back() 就会离站。 */
  const filterTo = useCallback(
    (tagName: string) =>
      router.replace(
        buildUrl((p) => {
          p.delete("photoId");
          p.set("tags", tagName);
        }),
        { scroll: false },
      ),
    [router, buildUrl],
  );

  return { photoId, direct, open, goto, close, filterTo };
}
