import type { Config } from "tailwindcss";

/** 暗房霓虹令牌映射：语义类 → styles/globals.css 的 CSS 变量。
 *  组件里不出现十六进制色值；一切色/圆角/字体/缓动走这里的语义名。 */
const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 背景层
        background: "var(--bg-page)",
        lightbox: "var(--bg-lightbox)",
        surface: "var(--bg-card)", // 实底卡 #15151c
        // 边框 / 分隔 / 白色填充层级
        border: "var(--border-glass)",
        "border-pop": "var(--border-pop)",
        strong: "var(--border-strong)",
        divider: "var(--divider)",
        "fill-1": "var(--fill-1)",
        "fill-2": "var(--fill-2)",
        "fill-3": "var(--fill-3)",
        // 文字四级（foreground = primary 的别名，供既有页面使用）
        foreground: "var(--text-primary)",
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        faint: "var(--text-faint)",
        label: "var(--text-label)",
        // 强调（渐变端色供 from-*/to-* 色标用；DEFAULT = 选中/星标紫）
        accent: {
          DEFAULT: "var(--accent-star)",
          from: "var(--accent-from)",
          to: "var(--accent-to)",
          fg: "var(--accent-fg)",
          soft: {
            edge: "var(--accent-soft-edge)",
            fg: "var(--accent-soft-fg)",
          },
        },
        ring: "var(--ring)",
        // 五分类标签色（chip 三件套：soft 底 / edge 边框 / fg 亮文字）
        character: {
          DEFAULT: "var(--cat-character)",
          soft: "var(--cat-character-soft)",
          edge: "var(--cat-character-edge)",
          fg: "var(--cat-character-fg)",
        },
        copyright: {
          DEFAULT: "var(--cat-copyright)",
          soft: "var(--cat-copyright-soft)",
          edge: "var(--cat-copyright-edge)",
          fg: "var(--cat-copyright-fg)",
        },
        artist: {
          DEFAULT: "var(--cat-artist)",
          soft: "var(--cat-artist-soft)",
          edge: "var(--cat-artist-edge)",
          fg: "var(--cat-artist-fg)",
        },
        meta: {
          DEFAULT: "var(--cat-meta)",
          soft: "var(--cat-meta-soft)",
          edge: "var(--cat-meta-edge)",
          fg: "var(--cat-meta-fg)",
        },
        general: {
          DEFAULT: "var(--cat-general)",
          soft: "var(--cat-general-soft)",
          edge: "var(--cat-general-edge)",
          fg: "var(--cat-general-fg)",
        },
        // 评级三色（同款三件套）
        safe: {
          DEFAULT: "var(--rating-safe)",
          soft: "var(--rating-safe-soft)",
          edge: "var(--rating-safe-edge)",
        },
        questionable: {
          DEFAULT: "var(--rating-q)",
          soft: "var(--rating-q-soft)",
          edge: "var(--rating-q-edge)",
        },
        explicit: {
          DEFAULT: "var(--rating-e)",
          soft: "var(--rating-e-soft)",
          edge: "var(--rating-e-edge)",
        },
      },
      backgroundImage: {
        // 渐变工具类（bg-grad-*），与色板名错开避免 bg-accent 冲突。
        "grad-accent": "linear-gradient(135deg, var(--accent-from), var(--accent-to))",
        "grad-accent-soft":
          "linear-gradient(135deg, var(--accent-soft-from), var(--accent-soft-to))",
        "grad-avatar": "linear-gradient(135deg, var(--avatar-from), var(--avatar-to))",
      },
      borderRadius: {
        pill: "var(--radius-pill)",
        card: "var(--radius-card)",
        table: "var(--radius-table)",
        panel: "var(--radius-panel)",
        modal: "var(--radius-modal)",
        thumb: "var(--radius-thumb)",
        "thumb-lg": "var(--radius-thumb-lg)",
      },
      fontFamily: {
        sans: ["var(--font-ui)"],
        ui: ["var(--font-ui)"],
        brand: ["var(--font-brand)"],
        mono: ["var(--font-mono)"],
      },
      boxShadow: {
        e1: "var(--shadow-e1)",
        e2: "var(--shadow-e2)",
        e3: "var(--shadow-e3)",
        glow: "var(--shadow-glow)",
        "focus-ring": "0 0 0 3px var(--ring-glow)",
      },
      transitionTimingFunction: {
        "out-soft": "var(--ease-out-soft)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-in-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "none" },
        },
        "slide-in-up": {
          from: { transform: "translateY(100%)" },
          to: { transform: "none" },
        },
      },
      animation: {
        "fade-in": "fade-in 150ms var(--ease-out-soft)",
        "fade-in-up": "fade-in-up 200ms var(--ease-out-soft) both",
        "slide-in-up": "slide-in-up 220ms var(--ease-out-soft) both",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
