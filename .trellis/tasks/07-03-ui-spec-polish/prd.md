# 按 ui-ux-pro-max 规范优化前端 UI

## Goal

对现有前端（Next.js 15 App Router，7 个页面/布局 + 15 个组件）做一次**规范符合性打磨**：按 ui-ux-pro-max 的 UX 规则（无障碍、交互、性能、风格一致性、布局、字体色彩、动效、表单反馈、导航）+ 项目自身前端规范（.trellis/spec/frontend/*）审计出的确认违规项，逐条修复。**不重设计、不加新功能、不改后端。**

## 背景

- 项目是类 Danbooru 深色沉浸式画廊，视觉身份已确立（暗色 token、玻璃拟态顶栏、标签分类色）。
- 代码基础质量较高（reduced-motion、token 化、字体 swap 已就位），本任务目标是消灭**残留的规范缺口**，把感知质量拉满。
- 审计方式：10 维度并行审计 + 按文件对抗复核 + 补漏批评员（多智能体工作流），只修"确认成立"的发现。

## Requirements

- R1 修复审计确认的 **critical / high** 级发现（无障碍与交互为主：对比度、焦点可达性、键盘路径、表单语义）。
- R2 修复 **medium** 级发现中改动小、收益明确的项（动效收敛、文案、truncation、autocomplete 等）。
- R3 **low / 架构级**发现只记录进任务 research 与 spec 备忘，不在本任务实施（如列表虚拟化）。
- R4 用户可见文案清理：不得出现开发黑话（工单号 "#8"、接口名等）。
- R5 修复过程不得违反项目约束（见下）。

## 硬约束

1. 桌面优先里程碑：移动触摸 UX 不在范围；<768px 只要求不破版。
2. 仅深色主题（html 固定 `dark`）。
3. 保持现有视觉身份：不换字体、不换品牌色、不重排布局。
4. 技术栈固定：Tailwind 工具类 + CSS 变量 token + shadcn/ui（源码自有）+ lucide-react。
5. 不加新功能（灯箱、收藏 API、新页面属后续切片）。
6. 键盘可达性是硬要求，不受桌面优先豁免。
7. TS strict、eslint 必须保持绿。

## Acceptance Criteria

- [ ] 审计确认清单中 critical/high 全部修复，medium 按 R2 处理，处理结果逐条可追溯（implement.md 勾选）。
- [ ] `cd frontend && npx tsc --noEmit` 与 `npm run lint` 全绿。
- [ ] `python dev.py` 启动后人工走查：登录 → 画廊浏览 → 搜索 → 标签抽屉 → 安全模式切换 → 设置页，纯键盘可完成且焦点始终可见。
- [ ] 375px / 768px / 1440px 三档宽度无横向滚动、无破版。
- [ ] 用户可见文案无开发黑话。
- [ ] 视觉身份不变（深色沉浸、玻璃拟态、标签分类色不动）。

## Notes

- 审计发现全文持久化在 `research/ui-audit-findings.md`（含被否决项及否决原因，防止后续重复报）。
- 技术设计见 `design.md`，执行清单见 `implement.md`。
