import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Providers } from "./providers";
import { Toaster } from "@/components/ui/sonner";
import "@/styles/globals.css";

// Self-hosted via next/font (zero deps, no FOIT — display:swap). The CSS
// variables are consumed by tailwind.config.ts fontFamily.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});
const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PM Gallery",
  description: "个人图库 — 深色沉浸式画廊",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // `dark` is fixed this milestone (dark immersive only).
  return (
    <html lang="zh-CN" className={`dark ${inter.variable} ${mono.variable}`}>
      <body className="min-h-dvh bg-background text-foreground antialiased">
        <Providers>{children}</Providers>
        <Toaster />
      </body>
    </html>
  );
}
