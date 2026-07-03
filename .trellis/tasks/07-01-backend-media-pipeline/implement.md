# 媒体处理管道 + 最小 Post 摄入 — 执行计划

> 配套 `prd.md` + `design.md`。按序执行，每步带校验命令与回滚点。

## 0. 前置（task.py start 前已完成的规划产物）
- [x] prd.md（7 条 AC）
- [x] design.md（8 节技术设计）
- [x] implement.md（本文件）

## 1. 加依赖

- [ ] **1.1** `backend/pyproject.toml` 的 `dependencies` 加 `"imagehash>=4.3"`。
- [ ] **1.2** 装包：`python -m pip install imagehash`（或 `uv pip install imagehash`）到 hermes venv。
- [ ] **1.3** 验证：`python -c "import imagehash; print(imagehash.__version__)"`。
  - **校验门**：import 成功且无 C 扩展编译。

## 2. DuplicateError

- [ ] **2.1** `backend/app/services/errors.py` 加 `class DuplicateError(AppError)`：`status_code=409`、`code="duplicate"`，放 `NotFoundError` 之后。
- [ ] **2.2** 验证：`python -c "from app.services.errors import DuplicateError; e=DuplicateError('x'); print(e.status_code, e.code)"` → `409 duplicate`。

## 3. media.py 核心内核

- [ ] **3.1** 新建 `backend/app/services/media.py`，写 `compute_md5`。
- [ ] **3.2** 写 `compute_phash`（`str(imagehash.phash(image))`）。
- [ ] **3.3** 写 `make_thumbnails`（RGB 转换 + 等比缩放 + PNG bytes；尺寸常量 `THUMB_SIZE=150`/`PREVIEW_SIZE=850`）。
- [ ] **3.4** 写 `ingest`（按 design.md §2 的 11 步流程：md5→去重→Pillow 解码→phash→缩略图→Post 占位→flush 拿 id→建目录落盘→回填路径→commit）。
- [ ] **3.5** 动图处理：ingest 内部 `is_animated` 时 `img.seek(0)` 取首帧传 `make_thumbnails`，original 存原始 `data`。
  - **校验门**：`python -c "from app.services import media; print(media.ingest, media.compute_md5, media.compute_phash, media.make_thumbnails)"` 全部可引用。

## 4. 测试 test_media.py

- [ ] **4.1** 新建 `backend/tests/test_media.py`，加 fixture 造真图字节（Pillow `Image.new` → PNG bytes）+ 用现有 `client`/`tmp_db_url` fixture。
- [ ] **4.2** `test_ingest_creates_files_and_post`（AC1）。
- [ ] **4.3** `test_ingest_md5_duplicate_raises`（AC2）。
- [ ] **4.4** `test_ingest_computes_phash`（AC3，含 Hamming 距离对照断言）。
- [ ] **4.5** `test_thumbnail_dimensions`（AC4，含 GIF 首帧静态）。
- [ ] **4.6** `test_ingest_rollback_on_disk_failure`（AC6，mock 落盘抛异常断言无残留行）。
  - **校验门**：`cd backend && python -m pytest tests/test_media.py -v` 全绿。

## 5. 迁移 seed_dev.py

- [ ] **5.1** `backend/scripts/seed_dev.py`：删 `_seed_posts` 里手写落盘 + Post 构造，改循环调 `media.ingest`。
- [ ] **5.2** `DuplicateError` 捕获后 `continue`（保幂等）。
- [ ] **5.3** 保留标签写入逻辑（`_get_or_create_tag` + `PostTag` + `post_count`）。
- [ ] **5.4** 删旧 `media/posts/{md5}/` 残留目录（dev only，重跑前清理）。
- [ ] **5.5** 手动验证：`python -m scripts.seed_dev` → 查 DB `Post.phash` 非空、preview 字节 ≠ original、目录 `posts/{id}/`。
  - **校验门**：seed 跑通、dev 浏览页视觉正常。

## 6. 全量回归

- [ ] **6.1** `cd backend && python -m pytest -v` → 原 25 + 新 media 测试全绿。
- [ ] **6.2** 确认 `imagehash` 在 `pyproject.toml`。
- [ ] **6.3** spec 自查：grep 确认无 `fav_count`、无 `create_all`、无 raw SQL、route 无业务逻辑（本切片无 route）。

## 校验命令汇总

```bash
cd backend
python -m pytest -v                                    # 全量（6.1）
python -m pytest tests/test_media.py -v                # 仅 media（4.6 后）
python -c "import imagehash; print(imagehash.__version__)"   # 1.3
python -m scripts.seed_dev                              # 5.5
```

## 回滚点

- **步骤 1 后**：删 imagehash 依赖即可，无代码改动。
- **步骤 2-3 后**：删 `media.py` + `DuplicateError`，DB 无影响。
- **步骤 5 后**（seed 迁移）：dev 库清空 `media/` + 重跑旧 seed（git checkout 旧版）即可。生产无数据。
- **全切片回滚**：`git revert` 本次提交，无 schema 迁移需反向。dev 重跑 seed。

## 风险点（来自 design.md §8）

- 损坏字节 `Image.open` 抛异常 → 不吞，留给切片 8 输入校验。
- flush 后落盘失败可能留空 `posts/{id}/` 目录 → 可接受，重跑 seed 清理。
