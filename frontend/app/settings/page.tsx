"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/lib/store/ui-store";

export default function SettingsPage() {
  const { theme, colorScheme, baseCurrency, setTheme, setColorScheme, setBaseCurrency } =
    useUiStore();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-h1 text-primary">设置</h1>
        <p className="text-small text-secondary">外观与展示偏好（本地保存）。</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>外观</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Row label="主题">
            <Button size="sm" variant={theme === "dark" ? "default" : "outline"} onClick={() => setTheme("dark")}>
              深色
            </Button>
            <Button size="sm" variant={theme === "light" ? "default" : "outline"} onClick={() => setTheme("light")}>
              浅色
            </Button>
          </Row>
          <Row label="涨跌色">
            <Button size="sm" variant={colorScheme === "western" ? "default" : "outline"} onClick={() => setColorScheme("western")}>
              绿涨红跌（美/日/港）
            </Button>
            <Button size="sm" variant={colorScheme === "asia" ? "default" : "outline"} onClick={() => setColorScheme("asia")}>
              红涨绿跌（A 股）
            </Button>
          </Row>
          <Row label="基准币种">
            {(["JPY", "USD", "CNY"] as const).map((c) => (
              <Button key={c} size="sm" variant={baseCurrency === c ? "default" : "outline"} onClick={() => setBaseCurrency(c)}>
                {c}
              </Button>
            ))}
          </Row>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI 与备份</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-small text-secondary">
          <p>AI 月度预算、券商费率、备份口令等在后端 <code className="text-primary">.env</code> 配置。</p>
          <p>AI 功能需配置 <code className="text-primary">ANTHROPIC_API_KEY</code>，缺失时相关功能优雅降级。</p>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-small text-secondary">{label}</span>
      <div className="flex gap-2">{children}</div>
    </div>
  );
}
