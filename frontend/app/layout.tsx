import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Noto_Sans_SC, Noto_Sans_JP } from "next/font/google";

import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { CommandPalette } from "@/components/layout/command-palette";
import { QueryProvider } from "@/components/providers/query-provider";
import { ThemeProvider } from "@/components/providers/theme-provider";
import { UpdaterProvider } from "@/components/providers/updater-provider";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans-latin", display: "swap" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });
// 高质量中日字体（自托管，覆盖简体中文与日文假名/汉字）
const notoSC = Noto_Sans_SC({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-sans-sc",
  display: "swap",
});
const notoJP = Noto_Sans_JP({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-sans-jp",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Hindsight",
  description: "记录、分析与复盘你的投资决策，对抗认知偏差。",
};

// 首屏前应用主题，消除 FOUC（主题闪烁）。在任何绘制前同步读取 localStorage。
const themeInitScript = `
(function () {
  try {
    var raw = localStorage.getItem('tradeai-ui');
    var theme = 'light', scheme = 'western';
    if (raw) {
      var s = JSON.parse(raw).state || {};
      if (s.theme) theme = s.theme;
      if (s.colorScheme) scheme = s.colorScheme;
    }
    var el = document.documentElement;
    el.classList.remove('dark', 'light');
    el.classList.add(theme);
    el.style.colorScheme = theme;
    el.setAttribute('data-color-scheme', scheme);
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="light" data-color-scheme="western" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={`${inter.variable} ${notoSC.variable} ${notoJP.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <ThemeProvider>
          <QueryProvider>
            <CommandPalette />
            <UpdaterProvider />
            <div className="flex h-screen w-screen overflow-hidden bg-base">
              <Sidebar />
              <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
                <Topbar />
                <main className="flex-1 overflow-y-auto">
                  <div className="mx-auto max-w-[1280px] px-6 py-6">{children}</div>
                </main>
              </div>
            </div>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
