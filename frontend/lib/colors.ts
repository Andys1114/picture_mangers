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
