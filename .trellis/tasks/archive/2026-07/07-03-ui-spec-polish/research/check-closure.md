# 检查阶段闭环报告（wf_7bf8861c-a59）

- 闭环核对：91 条判定 —— fixed 83 / recorded 1 / partial 7 / missed 0
- recorded（按设计只记录）：virtualize-lists@frontend/components/browse/masonry-grid.tsx

## partial（已在主会话全部补修，见下方处置）

- **press-feedback** @ frontend/components/ui/dropdown-menu.tsx：菜单项半边已修（L122 有 active:bg-surface/70，设计 D7 选定的变体），但触发按钮类串（L86 "inline-flex items-center justify-center h-10 w-10 rounded-md text-foreground hover:bg-surface cursor-pointer focus-visible:..."）仍无任何 active:* 态——fix 要求的触发钮 active:scale-[0.97] 未落地，而同批手写按钮（tag-drawer L17、safe-mode-toggle L38）都补上了。
- **press-feedback** @ frontend/components/browse/tag-drawer.tsx：L17 已加 active:scale-[0.97] 与 ease-out-soft，但缺 fix 明确要求的 transition duration-150——类串无任何 transition-* 工具类即 transition-property 未设，ease-out-soft 完全不生效，按压缩放与 hover:bg-surface 均瞬时切换（正是 fix 自述『只加 active 会显得生硬』的形态）。
- **press-feedback** @ frontend/components/browse/safe-mode-toggle.tsx：L38 已加 active:scale-[0.97]，但 transition-colors 未按 fix 改为 transition，transform 不在过渡属性内、按压缩放瞬时无过渡，与 Button 基线（transition duration-150 下的动画式按压）仍不一致。
- **easing** @ frontend/components/browse/safe-mode-toggle.tsx：锚点 safe-mode-toggle L38 已补 ease-out-soft（对 transition-colors 的颜色过渡生效）、settings 退出钮经 Button 基类获得 transition duration-150 ease-out-soft，但 fix 点名的第三处 badge.tsx L6 仍是裸 transition-colors 未补 token（审计 verify_note 自注该处无消费者、目前惰性）。
- **transform-performance** @ frontend/components/browse/post-card.tsx：L76 半条已修（transition-[opacity,background-color,transform] duration-200 ease-out-soft），但 L35 现为 transition-[transform,box-shadow]——虽从默认属性集收窄，e1→e2 阴影仍参与 200ms 逐帧动画，未按 fix「阴影改为直接切换（transition-transform）」处理，阴影重绘开销仍在，且该项不在 design.md 的「明确不做」清单。
- **error-clarity** @ frontend/app/login/page.tsx：login L39 兜底文案已改为「无法连接服务器，请确认后端已启动后重试」（含原因与补救，达成意图），但 fix 同时点名的 setup/page.tsx L45 仍是裸 setError(... : "创建失败")，设计文档 D10 只列了登录一处、未把 setup 记为不实施。
- **focus-management** @ frontend/app/setup/page.tsx：主体已实现：setup L20 passwordRef、L38 校验失败 passwordRef.current?.focus()、L84 ref 传入 PasswordInput；但 L88 aria-invalid 绑的是 !!error（fix 明确要求独立 pwdInvalid 状态，否则服务端「创建失败」会误标输入框），且 fix 中「login 在 onError 里聚焦用户名」未做（login L38-40 仅 setError）。

## 回归猎手发现（已在主会话全部修复）

- [low] sheet.tsx:37 — 新增的 body 滚动锁（overflow:hidden）会在打开抽屉瞬间移除滚动条，导致固定顶栏与瀑布流整体横向跳动约 17px（本次新引入：改动前 Sheet 无滚动锁，无此跳动）
- [medium] search-box.tsx:16 — New useEffect syncing input value from URL params can overwrite keystrokes the user types while a navigation is still committing (post-submit RSC roundtrip), silently discarding in-progress input.
- [medium] masonry-grid.tsx:21 — useColumnCount starts at 4 and only corrects after paint (useEffect), so any mount with cached data (e.g. back-nav from /settings within react-query gcTime) paints one frame at 4 columns and then redistributes every card; because cards move across `key={ci}` column parents, they unmount/remount — resetting PostCard `loaded` (shimmer + 300ms fade replay) and local `fav` state, and replaying the stagger entrance animation for the whole grid. Same full-grid blink occurs on every window resize across a breakpoint. The old CSS-columns layout was instantly correct with stable DOM.
- [low] search-box.tsx:26 — Switch from router.replace to router.push has no same-URL guard, so resubmitting an identical query (pressing Enter repeatedly is common) stacks duplicate history entries and makes the Back button appear dead until all duplicates are popped.
- [medium] D:\Workspace\picture_mangers\frontend\app\setup\page.tsx:73 — Newly added aria-invalid={!!error} on the username field falsely marks it invalid when the error is password-only ('密码至少 8 位') or a non-field server/network error. Trigger: enter a valid username + 7-char password, submit → focus correctly moves to password, but screen readers now announce the username field as 'invalid entry' even though it is fine. Before this change no false signal existed, so this is an accessibility semantics regression in the form's primary validation path.
- [low] D:\Workspace\picture_mangers\frontend\app\login\page.tsx:67 — aria-invalid={!!error} (lines 67 and 78) also fires for the new network-failure fallback error. Trigger: backend down → submit → error '无法连接服务器，请确认后端已启动后重试' → both username and password inputs are announced as invalid entries, misleading AT users into re-checking correct credentials when nothing is wrong with their input. (Flagging both fields for a genuine credential ApiError is accepted practice and not a defect; only the connection-error path is semantically false.)
- [low] D:\Workspace\picture_mangers\frontend\app\login\page.tsx:48 — The new checking-state skeleton (3 x h-10 rows + two 16px gaps = 152px) is ~48px shorter than the real form it stands in for (2 x [20px label + 4px + 40px input] + 40px button + two 16px gaps = 200px). AuthCard centers content vertically (min-h-dvh flex items-center justify-center), so when `checking` resolves the card grows 48px and recenters, shifting the logo/card ~24px — a visible one-time jump that falls short of the design's stated goal of a structurally congruent (同构) skeleton. Identical issue in setup/page.tsx lines 51-61.

## 处置记录（主会话修复）

1. dropdown 触发钮补 transition duration-150 ease-out-soft active:scale-[0.97]；tag-drawer/safe-mode 触发钮补 transition duration-150（ease 生效）；badge 补 duration-150 ease-out-soft。
2. post-card 卡片 transition 收敛为 transition-transform（阴影直接切换，不再逐帧重绘）。
3. setup 兜底错误文案改为「无法连接服务器…」；aria-invalid 改为 pwInvalid 仅在密码长度校验失败时标注（用户名不再误标）；login 的 aria-invalid 仅凭据错误（ApiError）时标注，网络失败不标；login onError 聚焦用户名。
4. globals.css html 补 scrollbar-gutter: stable（抽屉滚动锁不再引发 17px 横向跳动）。
5. search-box：输入框持焦时跳过 URL 同步（不覆盖草稿）；同 URL 重复提交不再压历史栈。
6. masonry useColumnCount 改惰性初始化（回退导航不再 4→N 列整格重挂闪烁）。
7. login/setup checking 骨架改为镜像表单行结构（2×[label+input]+按钮），高度一致无跳变。
8. 修复后 tsc --noEmit 与 next lint 均绿。