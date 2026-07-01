// Centralized query-key factory — never inline string keys (hook-guidelines).
import type { PostsParams } from "./types";

export const queryKeys = {
  me: () => ["me"] as const,
  posts: (params: { tags?: string; order?: string }) =>
    ["posts", { tags: params.tags ?? "", order: params.order ?? "id" }] as const,
  // Prefix key for invalidating every active posts list at once (e.g. after a
  // safe_mode flip, where the new rating filter applies to all tag/order
  // variants). Matches the `posts(params)` key prefix.
  postsAll: () => ["posts"] as const,
  post: (id: number) => ["post", id] as const,
} as const;

/** List params used by useInfinitePosts (tag filter + order). */
export type PostsQuery = Pick<PostsParams, "tags" | "order">;
