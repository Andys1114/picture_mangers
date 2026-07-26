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
}
