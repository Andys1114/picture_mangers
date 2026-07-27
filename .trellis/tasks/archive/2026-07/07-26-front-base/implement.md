# 前台基座与切换 · 执行清单

按序执行；每步结尾是验证命令。⛳ = 回滚点（该步独立成 commit，可单独 revert）。

## 阶段 A：目录切换

- [x] A1 `git mv frontend frontend-legacy`，纯改名提交 ⛳
  - 验证：`git log --follow -- frontend-legacy/lib/api.ts` 能看到改名前提交
- [x] A2 `frontend-legacy/README.md` 顶部加废弃横幅（已废弃/存档原因/新前端位置/如何手动运行），提交 ⛳
- [x] A3 新建 `frontend/` 脚手架：配置文件 + 移植 `next.config.ts`/`middleware.ts`/`lib/*`/`hooks/*`（见 design.md 2.1），`npm install`，一个临时首页可启动 ⛳
  - 验证：`python dev.py` 前后端都起来，`http://localhost:3000` 出临时页，登录门卫跳转 `/login` 正常

## 阶段 B：后端评级参数

- [x] B1 `search.list_posts` 加 `ratings` 过滤 + `api/posts.py` 参数解析校验；`lib/api.ts`/`useInfinitePosts` 同步加参 ⛳
  - 验证：`cd backend && python -m pytest tests/test_posts.py -q`（新增：安全模式开忽略参数/关时过滤/非法值 422/缺省全量 四个用例）

## 阶段 C：令牌与基础层

- [x] C1 `globals.css` 令牌全表 + 玻璃工具类 + reduced-motion；`tailwind.config.ts` 映射；fontsource 三字体接入 `app/layout.tsx`
- [x] C2 `components/ui/*` 按新令牌重写（button/badge/input/password-input/skeleton/sonner/dropdown-menu/sheet）
  - 验证：`npm run lint && npx tsc --noEmit`；临时页上渲染一组 ui 样品目测

## 阶段 D：前台桌面（对照 final-front.dc.html 逐屏验收）

- [x] D1 顶栏：胶囊壳 + logo + 搜索框（`/` 聚焦、空格 AND、回车提交进 `?tags=`）+ 安全模式按钮（PATCH + refetch + Toast）+ 用户菜单（用户名/退出登录）
- [x] D2 筛选栏：rail 壳 + 自动折叠（8s/悬停展开/图钉 localStorage）+ 已选 chips + 标签成组区（/api/tags/tree）+ 评级勾选（安全模式开禁用）；状态进 URL
- [x] D3 瀑布流 + 卡片：贪心最短列、无限滚动、fade-in-up、悬停态（无星标）
- [x] D4 中间态：骨架 shimmer / 空图库 / 无结果（放宽建议）/ 失败重试
- [x] D5 灯箱：URL 驱动开合与翻页（push/replace/back）、信息浮层（评级/操作/作者区/标签成组/元数据）、直达单图禁翻页、计数 chip
- [x] D6 登录/初始化页按设计稿样式（同壳玻璃卡；A3 已有功能版，这里只换皮） ⛳
  - 验证：浏览器走查——初始化→登录→浏览→筛选→灯箱←→→Esc→登出；对照设计稿截图比对

## 阶段 E：移动端（402 视口，对照 final-mobile.dc.html）

- [x] E1 首页响应式：搜索胶囊 + chips 行 + 双列瀑布流
- [x] E2 筛选抽屉：底部弹层（拖动把手、背景压暗、"应用筛选 · 显示 N 张"）
- [x] E3 灯箱手势：左右滑翻页、下滑关闭、信息半层上拉
- [x] E4 登录页移动样式
  - 验证：浏览器 402×874 视口全流程走查 + 截图比对

## 阶段 F：收口

- [x] F1 全量检查：`npm run lint`、`npx tsc --noEmit`、`cd backend && python -m pytest -q`；grep 确认无星标/收藏 UI、页面组件无硬编码色值
- [ ] F2 桌面 1280 + 移动 402 截图对照 `.dc.html`，偏差要么修掉要么记录进任务 notes
- [x] F3 更新 CONTEXT.md"浏览页"条目（筛选栏取代标签抽屉）；父任务 prd 勾掉本子任务

## 审查门

1. A3 后：骨架能跑再继续（防地基歪）。
2. D5 后：桌面全量走查通过再进移动端。
3. F 全过才算完，进入 3.x 收尾流程（spec 更新、commit）。
