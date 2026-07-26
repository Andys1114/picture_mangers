// Centralized query-key factory — never inline string keys (hook-guidelines).
import type { PostsParams } from "./types";

export const queryKeys = {
  me: () => ["me"] as const,
  posts: (params: { tags?: string; order?: string; ratings?: string }) =>
    [
      "posts",
      { tags: params.tags ?? "", order: params.order ?? "id", ratings: params.ratings ?? "" },
    ] as const,
  // Prefix key for invalidating every active posts list at once (e.g. after a
  // safe_mode flip, where the new rating filter applies to all tag/order
  // variants). Matches the `posts(params)` key prefix.
  postsAll: () => ["posts"] as const,
  post: (id: number) => ["post", id] as const,
  // 缺省值归一化：{} 与 {order:"count"} 落进同一份缓存。
  tags: (params: { search?: string; category?: string; order?: string }) =>
    [
      "tags",
      "list",
      {
        search: params.search ?? "",
        category: params.category ?? "",
        order: params.order ?? "count",
      },
    ] as const,
  tagTree: () => ["tags", "tree"] as const,
} as const;

/** List params used by useInfinitePosts (tag filter + order + rating subset). */
export type PostsQuery = Pick<PostsParams, "tags" | "order" | "ratings">;
