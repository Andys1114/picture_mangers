"use client";

import { useRef } from "react";

/** 滑动判定阈值（px）：水平 60 / 垂直 80（implement.md E3）。 */
const HORIZONTAL_MIN = 60;
const VERTICAL_MIN = 80;

export interface SwipeCallbacks {
  /** 手指向左滑（灯箱语义 = 下一张）。 */
  onSwipeLeft?: () => void;
  /** 手指向右滑（= 上一张）。 */
  onSwipeRight?: () => void;
  /** 上滑（信息半层展开）。 */
  onSwipeUp?: () => void;
  /** 下滑（信息层收起时 = 关闭灯箱；展开时 = 收起）。 */
  onSwipeDown?: () => void;
}

export interface SwipeHandlers {
  onPointerDown: (e: React.PointerEvent<HTMLElement>) => void;
  onPointerUp: (e: React.PointerEvent<HTMLElement>) => void;
  onPointerCancel: (e: React.PointerEvent<HTMLElement>) => void;
  onClickCapture: (e: React.MouseEvent<HTMLElement>) => void;
}

/** Pointer Events 滑动手势（touch/pen；鼠标拖拽不算滑动）。铺到目标元素上，
 *  配合 `touch-none` 防止浏览器把滑动吃成滚动/回退。
 *  按下时 setPointerCapture（手指移出元素仍能收到 up），抬起时一次性判定：
 *  - 横向占优（|dx| > |dy|）且 |dx| ≥ 60 → 左/右滑；
 *  - 纵向占优且 |dy| ≥ 80 → 上/下滑；
 *  - 两轴都不过阈值 = 点按，交给 click 正常处理。
 *  判定成功后吞掉紧随其后的合成 click（capture 阶段拦截），避免"滑动翻页
 *  顺带点了遮罩关闭"这类串触。回调缺省即该方向不响应（如直达单图禁翻页）。 */
export function useSwipe(callbacks: SwipeCallbacks): SwipeHandlers {
  const start = useRef<{ id: number; x: number; y: number } | null>(null);
  const consumed = useRef(false);

  return {
    onPointerDown: (e) => {
      if (e.pointerType === "mouse" || start.current !== null) return;
      consumed.current = false;
      start.current = { id: e.pointerId, x: e.clientX, y: e.clientY };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    onPointerUp: (e) => {
      const s = start.current;
      if (s === null || e.pointerId !== s.id) return;
      start.current = null;
      const dx = e.clientX - s.x;
      const dy = e.clientY - s.y;
      if (Math.abs(dx) > Math.abs(dy)) {
        if (Math.abs(dx) < HORIZONTAL_MIN) return;
        consumed.current = true;
        (dx < 0 ? callbacks.onSwipeLeft : callbacks.onSwipeRight)?.();
      } else {
        if (Math.abs(dy) < VERTICAL_MIN) return;
        consumed.current = true;
        (dy < 0 ? callbacks.onSwipeUp : callbacks.onSwipeDown)?.();
      }
    },
    onPointerCancel: (e) => {
      // 只清掉被跟踪指针的状态：多指时第二根手指的 cancel 不应打断首指手势。
      if (start.current?.id === e.pointerId) start.current = null;
    },
    onClickCapture: (e) => {
      if (!consumed.current) return;
      consumed.current = false;
      e.preventDefault();
      e.stopPropagation();
    },
  };
}
