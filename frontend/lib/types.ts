// Frontend types mirroring the backend Pydantic schemas (snake_case, matched
// exactly to avoid drift — see .trellis/spec/frontend/type-safety.md).
// No `fav_count`: favorited state is derived from membership, never a count.

export type Rating = "safe" | "questionable" | "explicit";
export type TagCategory = "general" | "character" | "copyright" | "artist" | "meta";

export interface User {
  id: number;
  username: string;
}

/** /api/auth/me response — user + per-session safe_mode (server-authoritative). */
export interface Me {
  id: number;
  username: string;
  safe_mode: boolean;
}

export interface Tag {
  id: number;
  name: string;
  category: TagCategory;
  post_count: number;
  is_deprecated: boolean;
}

/** List-item shape (no full tag set, to keep payload small). */
export interface PostSummary {
  id: number;
  preview_path: string;
  width: number;
  height: number;
  rating: Rating;
  is_animated: boolean;
  favorite: boolean;
}

/** Single-post detail (full fields + expanded tag set). */
export interface PostDetail extends PostSummary {
  file_path: string;
  thumb_path: string;
  source_site: string | null;
  source_url: string | null;
  md5: string;
  created_at: string;
  tags: Tag[];
}

/** GET /api/tags 查询参数（默认按 post_count 降序，服务端上限 200）。 */
export interface TagsParams {
  search?: string;
  category?: TagCategory;
  order?: "count" | "name";
}

/** /api/tags 成功信封（meta 目前恒为空对象）。 */
export interface TagListResponse {
  data: Tag[];
  meta: Record<string, unknown>;
}

/** /api/tags/tree 节点：一个子标签（antecedent）及其直接母标签（consequents）。
 *  注意方向：连带 A → B 表示"打了 A 就等于打了 B"，B 是母标签。 */
export interface TagTreeNode {
  tag: Tag;
  consequents: Tag[];
}

/** /api/tags/tree 成功信封（meta 目前恒为空对象）。 */
export interface TagTreeResponse {
  data: TagTreeNode[];
  meta: Record<string, unknown>;
}

/** GET /api/posts/{id}/next：灯箱 ←→ 翻页的前后图 id。
 *  全局 id 倒序视图（最新在前）、排除重复图、不随标签筛选变化；
 *  prev = 列表上一行（更新、id 更大），next = 下一行（更旧）。
 *  安全模式开启时服务端跳过非 safe 图。 */
export interface PostNextResponse {
  prev_id: number | null;
  next_id: number | null;
}

export interface PageMeta {
  page: number;
  total: number;
}

export interface Paginated<T> {
  data: T[];
  meta: PageMeta;
}

export interface ApiErrorBody {
  error: { code: string; message: string };
}

export interface PostsParams {
  tags?: string;
  page?: number;
  limit?: number;
  order?: "id" | "random";
  /** Comma-separated rating filter (wire format, e.g. "safe,questionable").
   *  Server-ignored while the session's safe mode is on; empty = all ratings. */
  ratings?: string;
}
