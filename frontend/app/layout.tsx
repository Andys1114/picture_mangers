import type { Metadata } from "next";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "PM Gallery",
  description: "个人图库 — 深色沉浸式画廊",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // `dark` is fixed this milestone (dark immersive only).
  return (
    <html lang="zh-CN" className="dark">
      <body className="min-h-dvh bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  );
}
