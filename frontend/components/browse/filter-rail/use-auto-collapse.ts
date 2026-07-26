"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const PIN_KEY = "rail_pinned";
const IDLE_MS = 8_000;

/** 筛选栏自动折叠状态机：
 *  - rail 内无操作（无 hover / 无焦点 / 无交互）8s 后收成 56px 图标条；
 *  - 悬停或聚焦即展开并暂停计时，离开后重新计时；
 *  - 图钉常驻（localStorage `rail_pinned`），常驻时不启动计时器；
 *  - 折叠/图钉是本地 UI 状态，不进 URL（state-management）。 */
export function useAutoCollapse() {
  const [pinned, setPinned] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const pinnedRef = useRef(false);
  const timerRef = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  /** 重新开始 8s 倒计时（图钉常驻时不计时）。 */
  const schedule = useCallback(() => {
    clearTimer();
    if (pinnedRef.current) return;
    timerRef.current = window.setTimeout(() => setCollapsed(true), IDLE_MS);
  }, [clearTimer]);

  // localStorage 是外来数据，只认 "1"（parse, don't trust）；
  // 首帧固定按未钉住渲染，避免 SSR 水合不一致。
  useEffect(() => {
    try {
      if (window.localStorage.getItem(PIN_KEY) === "1") {
        pinnedRef.current = true;
        setPinned(true);
        clearTimer();
        return;
      }
    } catch {
      // 隐私模式等场景下 localStorage 不可用，按未钉住处理。
    }
    schedule();
  }, [schedule, clearTimer]);

  // 卸载时清掉计时器。
  useEffect(() => clearTimer, [clearTimer]);

  const expand = useCallback(() => {
    setCollapsed(false);
    schedule();
  }, [schedule]);

  /** 手动折叠（标题行折叠钮）：立即收起，悬停即可再展开。 */
  const collapse = useCallback(() => {
    clearTimer();
    setCollapsed(true);
  }, [clearTimer]);

  const togglePin = useCallback(() => {
    const next = !pinnedRef.current;
    pinnedRef.current = next;
    setPinned(next);
    try {
      window.localStorage.setItem(PIN_KEY, next ? "1" : "0");
    } catch {
      // 写不进就只在本次会话生效。
    }
    clearTimer();
    if (next) setCollapsed(false);
    else schedule();
  }, [clearTimer, schedule]);

  /** 铺到 rail 容器上的交互监听：hover/焦点在内 = 展开 + 暂停计时。 */
  const containerProps = {
    onPointerEnter: () => {
      clearTimer();
      setCollapsed(false);
    },
    onPointerLeave: () => schedule(),
    onFocusCapture: () => {
      clearTimer();
      setCollapsed(false);
    },
    onBlurCapture: (e: React.FocusEvent<HTMLElement>) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) schedule();
    },
  };

  return { collapsed, pinned, expand, collapse, togglePin, containerProps };
}
