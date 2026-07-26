import type { Metadata } from "next";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";

// fontsource 自托管字体（unicode-range 分片，浏览器按需拉取，无外网依赖）：
// UI 中文 Noto Sans SC 400/500/700 · 品牌 Space Grotesk 500/700 ·
// id/路径/计数 JetBrains Mono 400/600。栈定义在 globals.css 的 --font-*。
import "@fontsource/noto-sans-sc/400.css";
import "@fontsource/noto-sans-sc/500.css";
import "@fontsource/noto-sans-sc/700.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "PM Gallery",
  description: "个人图库 — 深色沉浸式画廊",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // `dark` is fixed: the dark-room neon theme is single-theme by design.
  return (
    <html lang="zh-CN" className="dark">
      <body className="min-h-dvh bg-background font-ui text-primary antialiased">
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  );
}
