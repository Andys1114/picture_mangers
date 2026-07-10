# 后端审计修复：41 条确认项

## Goal

按 `docs/backend-audit-2026-07-04.md` 的 41 条确认发现（高 4 / 中 11 / 低 26），全部落地修复。每条按报告的「最小修复」执行，不过度设计。威胁模型保持：单用户本地/局域网部署。

## Requirements

- R1 修复全部 41 条确认项；同根因条目（#1/#2/#7、#12/#13、#26/#27、#10/#31）合并修复，需在实现说明中注明。
- R2 已否决的 4 条（login-brute-force、scan-path-unrestricted、posts n+1、errors catchall-no-logging）不修，不重复报告。
- R3 行为修正导致的旧测试断言变化允许调整，但必须对应审计条目并保持测试意图。
- R4 高危 4 条与中危 11 条必须新增回归测试覆盖（低危尽量补，成本高的可豁免）。
- R5 数据库结构变更（favorites.name 唯一约束、posts/favorite_items 索引）走 Alembic 迁移，必须能从现有数据升级（重名 favorites 先去重再加约束），并提供 downgrade。
- R6 不新增第三方依赖；httpx 从 dev extras 移入主依赖不算新增。
- R7 前端仅做类型同步（`frontend/lib/types.ts` 的 Tag 增加 is_deprecated），不做 UI 改动；favorite 字段前端已按 boolean 消费，无需改动。
- R8 遵守 `.trellis/spec/backend/` 全部规范（directory-structure / database-guidelines / error-handling / quality-guidelines / logging-guidelines）。

## Acceptance Criteria

- [x] AC1 `cd backend && ./.venv/Scripts/python -m pytest -q` 全绿（原 63 例 + 新增回归测试）。
- [x] AC2 高危 4 条各有回归测试：ingest 失败后 rollback（无孤儿 Post）、PATCH 保留 implication 后件、删除 post 递减 post_count、（#2 与 #1 合并）。
- [x] AC3 中危 11 条各有回归测试或等效验证（如 pyproject 依赖移动为静态检查）。
- [x] AC4 /media 未登录返回 401，登录后可取图且带 `Cache-Control: public, max-age=31536000, immutable`，路径穿越被拒。
- [x] AC5 favorite 字段在 list/detail/patch 响应中真实反映收藏状态（toggle 后刷新不丢星标）。
- [x] AC6 scrape 任务进度逐帖更新、取消在下一帖生效。
- [x] AC7 422 校验错误返回统一错误信封 `{"error":{"code":"validation_error","message":...}}`。
- [x] AC8 任务失败响应不再含 str(exc) 原文，服务端日志有完整异常记录。
- [x] AC9 迁移 upgrade/downgrade 在测试中通过（conftest 走 upgrade head）。
- [x] AC10 41 条逐条核对：每条有代码变更，或注明「与 #N 合并修复」。

## 约束

- 不改 README 已知约束（Danbooru 真实抓取被 Cloudflare 拦截）相关行为。
- 保持 API 路径与响应形状兼容（新增字段可以，删除/改名不可以），前端不感知破坏性变化。
- /media URL 形状保持 `/media/<相对路径>` 不变（Next.js rewrite 依赖）。
