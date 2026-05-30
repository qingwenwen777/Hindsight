"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { LOCALES } from "@/lib/i18n/messages";
import { useT } from "@/lib/i18n/use-t";
import { useUiStore } from "@/lib/store/ui-store";

export default function SettingsPage() {
  const { t } = useT();
  const {
    theme,
    colorScheme,
    baseCurrency,
    locale,
    setTheme,
    setColorScheme,
    setBaseCurrency,
    setLocale,
  } = useUiStore();

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("settings.title")}</h1>
        <p className="text-small text-secondary">{t("settings.subtitle")}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("settings.appearance")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Row label={t("settings.language")}>
            {LOCALES.map((l) => (
              <Button
                key={l.value}
                size="sm"
                variant={locale === l.value ? "default" : "outline"}
                onClick={() => setLocale(l.value)}
              >
                {l.label}
              </Button>
            ))}
          </Row>
          <Row label={t("settings.theme")}>
            <Button size="sm" variant={theme === "dark" ? "default" : "outline"} onClick={() => setTheme("dark")}>
              {t("settings.dark")}
            </Button>
            <Button size="sm" variant={theme === "light" ? "default" : "outline"} onClick={() => setTheme("light")}>
              {t("settings.light")}
            </Button>
          </Row>
          <Row label={t("settings.colorScheme")}>
            <Button size="sm" variant={colorScheme === "western" ? "default" : "outline"} onClick={() => setColorScheme("western")}>
              {t("settings.western")}
            </Button>
            <Button size="sm" variant={colorScheme === "asia" ? "default" : "outline"} onClick={() => setColorScheme("asia")}>
              {t("settings.asia")}
            </Button>
          </Row>
          <Row label={t("settings.baseCurrency")}>
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
          <CardTitle>{t("settings.aiBackup")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-small text-secondary">
          <p>{t("settings.aiBackupDesc1")}</p>
          <p>{t("settings.aiBackupDesc2")}</p>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="shrink-0 text-small text-secondary">{label}</span>
      <div className="flex flex-wrap justify-end gap-2">{children}</div>
    </div>
  );
}
