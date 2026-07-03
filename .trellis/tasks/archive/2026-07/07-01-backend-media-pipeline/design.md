# 媒体处理管道 + 最小 Post 摄入 — 技术设计

> 配套 `prd.md`。本切片为 `06-28-gallery-app` design.md §4「共享媒体处理管道」的实现，但**收窄**到「摄入内核」，不含抓取/导入调度/API。

## 1. 模块边界

```
backend/app/services/media.py        ← 新增：媒体处理内核（本切片核心）
backend/app/services/errors.py       ← 改：加 DuplicateError
backend/scripts/seed_dev.py          ← 改：迁移到 media.ingest
backend/tests/test_media.py          ← 新增：端到端单测
backend/pyproject.toml               ← 改：加 imagehash 依赖
```

**不碰**：`api/`、`schemas/`、`models/`、`alembic/`、`deps.py`、`db.py`、`config.py`。

层级守约：`media.py` 是 service 层，**不导入 fastapi/httpx**，只用 Pillow/imagehash/SQLAlchemy ORM。它被未来的 import API（切片 8）和 scraper（切片 4）调用，但本切片不写任何调用方（除 seed_dev 这个 dev 脚本）。

## 2. 数据流（ingest 核心）

```
ingest(db, data: bytes, *, source_*, file_ext, is_animated, rating) -> Post
  │
  ├─ 1. md5 = compute_md5(data)
  ├─ 2. 查 Post.md5 == md5 → 命中抛 DuplicateError（不落盘、不建行）
  ├─ 3. img = Image.open(BytesIO(data))         # Pillow 解码
  ├─ 4. width, height = img.size
  ├─ 5. phash = compute_phash(img)              # imagehash，hex str
  ├─ 6. thumb_b, preview_b = make_thumbnails(img)
  ├─ 7. post = Post(md5=..., phash=..., width=..., height=..., file_size=len(data),
  │                 file_ext=..., is_animated=..., rating=..., source_*=...,
  │                 file/thumb/preview_path=占位)  # 先占位，flush 后回填
  ├─ 8. db.add(post); db.flush()                # 拿 post.id（不 commit）
  ├─ 9. rel = f"posts/{post.id}"
  │     media_dir = settings.media_path
  │     post_dir = media_dir / rel; post_dir.mkdir(parents=True, exist_ok=True)
  │     写 original.{ext} / preview.png / thumb.png
  ├─10. 回填 post.file_path/thumb_path/preview_path = f"{rel}/..."
  └─11. db.commit(); db.refresh(post); return post
```

**id 先有鸡先有蛋的解法**：步骤 8 `flush`（不发 INSERT 的 COMMIT，但拿自增 id）→ 步骤 9 用 id 建目录 → 步骤 10 回填路径 → 步骤 11 commit。落盘失败（磁盘满等）会抛异常，因尚未 commit，session 在调用方（`get_db` 的 finally close 或测试 fixture）回滚，**不留半残 Post 行**。

**路径约定**：DB 存相对路径 `posts/{id}/original.png`；落盘用 `settings.media_path / "posts" / str(id)` 绝对路径。StaticFiles 挂在 `/media`，所以前端访问 `/media/posts/{id}/preview.png` 同源。

## 3. 决策记录（与 spec/父 design 的调和）

| # | 决策 | 依据 / 偏差说明 |
|---|---|---|
| D1 | 边界 = 服务 + 最小 Post 写入（非纯函数） | 纯函数留 `id` 悬空（目录依赖 id）。写入 Post 是切片 4/8 复用的最小内核，不扩到 API/调度。 |
| D2 | phash 用 `imagehash` 库 | 用户选「稳健性」。imagehash 纯 Python、依赖 Pillow、无 C 扩展，是合理新依赖。比手搓 DCT pHash 更可靠。 |
| D3 | phash **同步算值存字段**、**查邻标记留异步** | spec 写「phash 异步后算」，本切片调和：算 phash 值（一次 imagehash.phash 调用）快，同步存；查 phash 近邻（需扫库算 Hamming）慢，留切片 4/8 调度器。故 ingest 后 `phash` 非空但 `is_duplicate=False`、`duplicate_of_id=None`。 |
| D4 | 动图缩略图取首帧、原图保留动画 | 父 design 明确。`ImageSequence` 取首帧做 thumb/preview，original 原样存 bytes（保留 GIF/APNG 动画）。`is_animated` 由调用方传入（抓取/导入知道格式）。 |
| D5 | 存盘 `posts/{id}/` 非 `posts/{md5}/` | seed_dev 旧用 md5 分目录，本切片统一为 id（更稳定：md5 去重后同一图只一行，id 是 PK，目录与行一一对应）。**迁移 seed_dev 时一并改**。 |
| D6 | md5 命中抛 `DuplicateError`（非静默跳过） | seed_dev 旧 `continue` 静默。服务层应让上层决策（抓取器：跳过+记日志；导入：跳过+计重复数）。`DuplicateError(AppError)` code=`duplicate` HTTP=409。 |
| D7 | 摄入入口吃 bytes 不吃路径 | 抓取器下载得 bytes、本地导入读文件成 bytes，统一接口；服务层不关心字节来源。 |

## 4. 接口契约

```python
# services/media.py
from __future__ import annotations
import hashlib, io
from pathlib import Path
from PIL import Image
import imagehash
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import settings
from app.models.post import Post
from app.services.errors import DuplicateError

THUMB_SIZE = 150
PREVIEW_SIZE = 850

def compute_md5(data: bytes) -> str: ...            # hashlib.md5(data).hexdigest()
def compute_phash(image: Image.Image) -> str: ...   # str(imagehash.phash(image))  # hex
def make_thumbnails(image: Image.Image) -> tuple[bytes, bytes]: ...
    # 转 RGB（RGBA/P 落白底）、等比缩放（ImageOps.contain / Thumbnail），
    # thumb→THUMB_SIZE、preview→PREVIEW_SIZE，存 PNG bytes。
    # 动图：调用方传首帧 Image（ingest 内部用 ImageSequence 取首帧）。
def ingest(db, data, *, source_site, source_id, source_url,
           file_ext, is_animated, rating="safe") -> Post: ...

# services/errors.py 新增
class DuplicateError(AppError):
    status_code = 409
    code = "duplicate"
```

**`make_thumbnails` 的动图处理**：ingest 内部 `Image.open` 后，若 `is_animated` 取 `img.seek(0)` 首帧传给 `make_thumbnails`；original 存原始 `data`（保留动画）。这样 thumb/preview 永远是静态首帧 PNG。

## 5. seed_dev 迁移

`seed_dev.py` 现状是手搓 PNG + 手写落盘 + 静默 md5 跳过。迁移为：

- 保留 `_png_solid`（造测试字节流，dev 用，不引入 Pillow 造图也行，但 `_png_solid` 已能用且零依赖）。
- 删 `_seed_posts` 里的手写落盘 + Post 构造，改为循环调 `media.ingest(db, png, source_site="local", source_id=None, ...)`。
- `DuplicateError` 捕获后 `continue`（seed 幂等语义不变，只是从「查 md5 静默跳过」变成「ingest 抛 + 捕获跳过」）。
- 标签写入仍由 seed 自己做（本切片不碰标签物化，seed 现有的 `_get_or_create_tag` + `PostTag` + `post_count += 1` 保留）。
- 目录结构自动从 `{md5}/` 变 `{id}/`（ingest 内部决定）。

## 6. 测试设计（test_media.py）

fixture：用 Pillow 现造真图字节（`Image.new("RGB",(w,h),color)` → PNG bytes），或复用 `_png_solid`。用 `client`/`tmp_db_url` fixture 拿 tmp DB + migrated schema。

- `test_ingest_creates_files_and_post` — AC1：断言三文件存在、Post 字段、相对路径。
- `test_ingest_md5_duplicate_raises` — AC2：二次 ingest 抛 DuplicateError、无第二行、无第二目录。
- `test_ingest_computes_phash` — AC3：phash 非空；同图缩放后 Hamming < 8、异图 > 20（用 imagehash.hex_to_hash 算距离）。
- `test_thumbnail_dimensions` — AC4：thumb ≤150、preview ≤850；GIF 首帧静态、`is_animated=True`。
- `test_ingest_rollback_on_disk_failure` — AC6：mock 落盘抛异常，断言无 Post 行残留（事务回滚）。
- `test_seed_dev_uses_pipeline`（可选，或手动验证）— AC5：跑 `seed_dev.main`，断言 phash 非空、preview≠original 字节、`posts/{id}/` 结构。

## 7. 兼容性 / 回滚

- **无 schema 变更**，无迁移风险。
- `imagehash` 新依赖：若回滚，删依赖 + 还原 media.py/seed_dev.py/errors.py 即可，DB 无影响。
- 存盘结构 `{md5}/` → `{id}/`：**dev 库需清空 `media/` 重跑 seed**。生产此刻无数据，无迁移负担。在 implement.md 标注此操作步骤。
- 旧 seed 数据（如有）目录名是 md5，新管道按 id——不兼容，重跑 seed 即可（dev only）。

## 8. 风险

- **`Image.open` 对损坏字节抛异常**：ingest 不吞，让全局 handler 返回 400。本切片不专门处理（切片 8 导入 API 会加输入校验）。
- **`flush` 后落盘失败的事务语义**：SQLite + SQLAlchemy，flush 未 commit，session rollback 撤销 INSERT。但已建的空目录 `posts/{id}/` 可能残留（mkdir 成功后写文件失败）。implement 标注：可接受残留空目录（下次同 id 复用，或重跑 seed 清理），不为此加复杂清理逻辑。
