import type { LucideIcon } from "lucide-react";
import { Shield, ShieldAlert, ShieldX } from "lucide-react";
import type { Rating, TagCategory } from "./types";

/** Rating → Tailwind class for the colored corner block on a card. */
export function ratingColor(r: Rating): { bg: string; text: string } {
  switch (r) {
    case "safe":
      return { bg: "bg-safe", text: "text-safe" };
    case "questionable":
      return { bg: "bg-questionable", text: "text-questionable" };
    case "explicit":
      return { bg: "bg-explicit", text: "text-explicit" };
  }
}

/** Rating → lucide icon, so the rating chip conveys meaning via icon+text+color
 *  (not color alone — spec: color-not-only). */
export function ratingIcon(r: Rating): LucideIcon {
  switch (r) {
    case "safe":
      return Shield;
    case "questionable":
      return ShieldAlert;
    case "explicit":
      return ShieldX;
  }
}

/** Rating → short chip label (Danbooru convention: safe/q/e). */
export function ratingLabel(r: Rating): string {
  switch (r) {
    case "safe":
      return "safe";
    case "questionable":
      return "q";
    case "explicit":
      return "e";
  }
}

/** Tag category → Tailwind classes for chips (PRD F2 / component-guidelines). */
export function tagCategoryColor(c: TagCategory): string {
  switch (c) {
    case "character":
      return "bg-accent/20 text-accent border-accent/40";
    case "copyright":
      return "bg-purple-500/20 text-purple-300 border-purple-500/40";
    case "artist":
      return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    case "meta":
      return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
    case "general":
    default:
      return "bg-surface text-muted border-border";
  }
}
