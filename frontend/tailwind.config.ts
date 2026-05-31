import type { Config } from "tailwindcss";

/**
 * Tailwind 配置 —— 仿 Hindsight / TradingView 深色视觉系统。
 * 所有颜色走 CSS 变量（见 app/globals.css），支持深/浅主题与涨跌色切换。
 */
const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 背景层级
        base: "var(--bg-base)",
        surface: "var(--bg-surface)",
        elevated: "var(--bg-elevated)",
        // 边框三级
        "border-subtle": "var(--border-subtle)",
        "border-default": "var(--border-default)",
        "border-strong": "var(--border-strong)",
        border: "var(--border-default)",
        // 文字层级
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        tertiary: "var(--text-tertiary)",
        muted: "var(--text-muted)",
        // 语义色
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-foreground": "var(--accent-foreground)",
        "btn-primary": "var(--btn-primary-bg)",
        "btn-primary-fg": "var(--btn-primary-fg)",
        up: "var(--up)",
        down: "var(--down)",
        warn: "var(--warn)",
        danger: "var(--danger)",
        // shadcn 兼容别名
        background: "var(--bg-base)",
        foreground: "var(--text-primary)",
        ring: "var(--accent)",
        input: "var(--border-default)",
      },
      fontFamily: {
        sans: [
          "var(--font-sans-latin)",
          "var(--font-sans-sc)",
          "var(--font-sans-jp)",
          "PingFang SC",
          "Hiragino Sans",
          "Microsoft YaHei",
          "system-ui",
          "sans-serif",
        ],
        mono: ["var(--font-mono)", "JetBrains Mono", "Roboto Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        // 字号阶梯（Hindsight）
        kpi: ["36px", { lineHeight: "1", fontWeight: "500" }],
        display: ["24px", { lineHeight: "1.2", fontWeight: "500" }],
        h1: ["24px", { lineHeight: "1.2", fontWeight: "500" }],
        h2: ["14px", { lineHeight: "1.25", fontWeight: "500" }],
        title: ["14px", { lineHeight: "1.25", fontWeight: "500" }],
        body: ["14px", { lineHeight: "1.55", fontWeight: "400" }],
        small: ["13px", { lineHeight: "1.45", fontWeight: "400" }],
        meta: ["13px", { lineHeight: "1.35", fontWeight: "400" }],
        caption: ["11px", { lineHeight: "1.2", fontWeight: "400" }],
        badge: ["10px", { lineHeight: "1.2", fontWeight: "500" }],
        "mono-lg": ["18px", { lineHeight: "1.4", fontWeight: "500" }],
        "mono-sm": ["13px", { lineHeight: "1.4", fontWeight: "400" }],
      },
      borderRadius: {
        sm: "3px",
        badge: "3px",
        md: "8px",
        lg: "16px",
        card: "16px",
        pill: "999px",
      },
      spacing: {
        "1": "4px",
        "2": "8px",
        "3": "12px",
        "4": "16px",
        "5": "20px",
        "6": "24px",
        "8": "32px",
      },
      keyframes: {
        // 纯透明度淡入（reduced-motion 兜底用）
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        // 内容入场：极小上移 + 淡入（位移 4px，时长短）
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        // 数值更新闪色：背景闪一下对应涨跌色再淡出
        // （用 --flash-up/down 变量，已在 globals.css 做 rgba 兜底 + color-mix 覆盖）
        "flash-up": {
          "0%": { backgroundColor: "var(--flash-up)" },
          "100%": { backgroundColor: "transparent" },
        },
        "flash-down": {
          "0%": { backgroundColor: "var(--flash-down)" },
          "100%": { backgroundColor: "transparent" },
        },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out both",
        "fade-in-up": "fade-in-up 200ms ease-out both",
        "flash-up": "flash-up 440ms ease-out",
        "flash-down": "flash-down 440ms ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
