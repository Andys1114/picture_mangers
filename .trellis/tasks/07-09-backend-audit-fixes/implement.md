# 执行计划：后端审计修复

## 前置

- [x] 基线确认：backend/.venv 已建，`pytest -q` 63 例全绿（2026-07-09）。
- [x] prd.md / design.md / implement.jsonl / check.jsonl 就绪。

## 执行清单（按序）

1. [x] `task.py start` 激活任务。
2. [x] 并行派发 5 个 trellis-implement 子代理（W1–W5，文件所有权见 design.md，严禁越界改文件；conftest.py 仅 W3 可改）。每个子代理：
   - 读 `docs/backend-audit-2026-07-04.md` 中自己负责的条目详情（含复核意见）。
   - 读 implement.jsonl 列出的规范文档。
   - 按 design.md 对应小节实现 + 补回归测试。
   - 只跑自己范围的测试文件确认通过（全量集成由主线程做）。
   - 不 git commit。
3. [x] 集成验证：全量 `pytest -q`，修复跨包冲突/回归（主线程处理）。
4. [x] 对抗复核：按包派发 trellis-check 子代理，逐条核对 41 项「已修/合并修复」；发现问题回到步骤 3。
5. [x] AC10 清单核对（prd.md 验收标准逐条打勾）。
6. [x] 规范更新（3.3）：如有约定变化（如 tag_post 的 commit 参数、/media 认证路由），补进 .trellis/spec/backend 对应文档。
7. [x] 提交（3.4）：单 commit `fix(backend): 后端审计修复——按 41 条确认项修复`，附 docs/backend-audit-2026-07-04.md 一并入库。

## 验证命令

```
cd backend && ./.venv/Scripts/python -m pytest -q
```

## 回滚点

- 实现前工作区干净（仅 docs/backend-audit-2026-07-04.md untracked），出问题 `git checkout -- backend/ frontend/` 即回滚。
- 迁移带 downgrade；数据库为本地 SQLite，测试环境每例重建。

## 复核门

- 步骤 3 全量测试全绿才能进步骤 4。
- 步骤 4 全部条目确认才能提交。
