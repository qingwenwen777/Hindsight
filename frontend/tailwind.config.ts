import type { Config } from "tailwindcss";

/**
 * Tailwind 配置 —— 落地设计文档 8.2 节 Design Tokens。
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
        // 边框
        "border-subtle": "var(--border-subtle)",
        border: "var(--border-subtle)",
        // 文字层级
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        // 语义色
        accent: "var(--accent)",
        "accent-foreground": "var(--accent-foreground)",
        up: "var(--up)",
        down: "var(--down)",
        warn: "var(--warn)",
        danger: "var(--danger)",
        // shadcn 兼容别名
        background: "var(--bg-base)",
        foreground: "var(--text-primary)",
        ring: "var(--accent)",
        input: "var(--border-subtle)",
      },
      fontFamily: {
        sans: ["Inter", "PingFang SC", "Microsoft YaHei", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Roboto Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        // 字号阶梯（文档 8.2）
        display: ["28px", { lineHeight: "1.2", fontWeight: "600" }],
        h1: ["20px", { lineHeight: "1.3", fontWeight: "600" }],
        h2: ["16px", { lineHeight: "1.4", fontWeight: "600" }],
        body: ["14px", { lineHeight: "1.5", fontWeight: "400" }],
        small: ["13px", { lineHeight: "1.5", fontWeight: "400" }],
        caption: ["12px", { lineHeight: "1.4", fontWeight: "400" }],
        "mono-lg": ["18px", { lineHeight: "1.4", fontWeight: "500" }],
        "mono-sm": ["13px", { lineHeight: "1.4", fontWeight: "400" }],
      },
      borderRadius: {
        sm: "4px",
        md: "6px",
        lg: "8px",
      },
      spacing: {
        // 8 基准间距
        "1": "4px",
        "2": "8px",
        "3": "12px",
        "4": "16px",
        "6": "24px",
        "8": "32px",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
