# 执行计划 — 前端视觉美化打磨

> 纯 Tailwind/CSS，零新依赖。每步带验证。完成后跑 trellis-check。

## 验证命令
```bash
cd frontend && npm run lint && npx tsc --noEmit && npm run build
# 联调（后端 :8000 + 前端 :3000 已在后台跑）
```

## 清单

### A. 字体 + token
- [ ] A1. `app/layout.tsx`：next/font Inter + JetBrains_Mono（variable + display swap），挂 `<html>`。
- [ ] A2. `tailwind.config.ts`：fontFamily 用 `var(--font-sans/mono)` + fallback；扩展 boxShadow e1/e2、ringColor、keyframes fade-in-up/shimmer、animation tokens。
- [ ] A3. `styles/globals.css`：增补 token（elevation、ring、shimmer、dur/ease）；reduced-motion 段保留并覆盖新动画。
- [ ] 验证：`tsc --noEmit` 通过；dev 起来字体生效。

### B. 公共组件
- [ ] B1. `components/ui/button.tsx`：加 `active:scale-[0.97] transition-transform duration-150`；focus ring 统一。
- [ ] B2. `components/ui/skeleton.tsx`：加 shimmer 渐变扫描类。
- [ ] B3. `components/common/auth-card.tsx`（新）：品牌 wordmark + tagline + 径向渐变背景 slot + 卡片壳，供 login/setup 复用。
- [ ] B4. `lib/colors.ts`：加 rating 图标映射（ratingIcon(r) → lucide 组件名），不改既有 ratingColor 签名。
- [ ] 验证：`tsc --noEmit`。

### C. 登录/向导/设置页
- [ ] C1. `app/login/page.tsx`：用 AuthCard；密码 show/hide 切换（Eye/EyeOff + aria-label）。
- [ ] C2. `app/setup/page.tsx`：用 AuthCard；密码 show/hide；helper text「≥8 位」。
- [ ] C3. `app/settings/page.tsx`：三段卡片（安全模式/账户/关于）。
- [ ] 验证：手动看三页视觉 + 密码切换。

### D. 顶栏
- [ ] D1. `components/browse/topbar.tsx`：logo 加 Images 图标；底部分隔渐变；scroll hidden 加 opacity；icon button active:scale。
- [ ] 验证：浏览页顶栏视觉 + 滚动渐隐。

### E. 瀑布流卡片 + 网格
- [ ] E1. `components/browse/post-card.tsx`：hover scale + shadow；图片 onLoad 淡入；底部渐变遮罩；分级 chip（色+文+图标）；★ 加 `card-fav` 类 + 精修。
- [ ] E2. `components/browse/masonry-grid.tsx`：stagger 入场（`--i` inline + fade-in-up，封顶 6）；shimmer skeleton；空态加 ImageOff 图标；`isError` 重试按钮。
- [ ] E3. globals.css `@media (hover:none) .card-fav { opacity:1 }`。
- [ ] 验证：浏览页 hover、触屏 ★ 可见、stagger、skeleton、空/错态。

### F. 质量回归
- [ ] F1. lint/tsc/build 干净。
- [ ] F2. 375px 不溢出；reduced-motion 降级；对比度 AA。
- [ ] F3. 功能回归：setup→login→浏览→无限滚动→安全模式切换。
- [ ] F4. trellis-check 过质量门。

## 风险/回滚
- next/font 在离线/受限网络首次构建会拉 Google Fonts——若网络受限，fallback 到本地字体栈（保留 fallback），不阻塞。
- 全是视觉改动，回滚 = git revert 单提交。
