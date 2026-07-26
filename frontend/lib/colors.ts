import type { LucideIcon } from "lucide-react";
import { Ban, Shield, TriangleAlert } from "lucide-react";
import type { Rating, TagCategory } from "./types";

// 分类色 / 评级色 → Tailwind 类名映射（令牌见 styles/globals.css）。
// chip 三件套统一为：15% 底 + 40% 边框 + 亮文字。

/** 评级 → chip 三件套类名（底/边框/文字），给评级 chip 用。 */
export function ratingColor(r: Rating): string {
  switch (r) {
    case "safe":
      return "bg-safe-soft border-safe-edge text-safe";
    case "questionable":
      return "bg-questionable-soft border-questionable-edge text-questionable";
    case "explicit":
      return "bg-explicit-soft border-explicit-edge text-explicit";
  }
}

/** 评级 → 纯文字色类名（勾选项/图标等非 chip 场景）。 */
export function ratingTextColor(r: Rating): string {
  switch (r) {
    case "safe":
      return "text-safe";
    case "questionable":
      return "text-questionable";
    case "explicit":
      return "text-explicit";
  }
}

/** 评级 → lucide 图标（对应设计稿 shield / warning / block），
 *  评级信息靠 图标+文字+颜色 三者传达，不只靠颜色。 */
export function ratingIcon(r: Rating): LucideIcon {
  switch (r) {
    case "safe":
      return Shield;
    case "questionable":
      return TriangleAlert;
    case "explicit":
      return Ban;
  }
}

/** 评级 → chip 文案（设计稿定稿："S 安全 / Q 擦边 / E 露骨"）。 */
export function ratingLabel(r: Rating): string {
  switch (r) {
    case "safe":
      return "S 安全";
    case "questionable":
      return "Q 擦边";
    case "explicit":
      return "E 露骨";
  }
}

/** 标签分类 → chip 三件套类名（底/边框/文字）。 */
export function tagCategoryColor(c: TagCategory): string {
  switch (c) {
    case "character":
      return "bg-character-soft border-character-edge text-character-fg";
    case "copyright":
      return "bg-copyright-soft border-copyright-edge text-copyright-fg";
    case "artist":
      return "bg-artist-soft border-artist-edge text-artist-fg";
    case "meta":
      return "bg-meta-soft border-meta-edge text-meta-fg";
    case "general":
    default:
      return "bg-general-soft border-general-edge text-general-fg";
  }
}

/** 标签分类 → 基色圆点/分布条类名（筛选栏作者圆点、统计分布条用）。 */
export function tagCategoryDotColor(c: TagCategory): string {
  switch (c) {
    case "character":
      return "bg-character";
    case "copyright":
      return "bg-copyright";
    case "artist":
      return "bg-artist";
    case "meta":
      return "bg-meta";
    case "general":
    default:
      return "bg-general";
  }
}
