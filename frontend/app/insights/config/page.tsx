"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ProviderModelPicker } from "@/components/ai/provider-model-picker";
import { useT } from "@/lib/i18n/use-t";
import { useReportConfig, useSaveReportConfig } from "@/lib/hooks/use-insights";
import { cn } from "@/lib/utils";

const MARKETS = ["US", "CN", "HK", "JP"];
const DEFAULT_TIME: Record<string, string> = { US: "06:30", CN: "16:30", HK: "17:30", JP: "16:00" };

export default function ReportConfigPage() {
  const { t } = useT();
  const { data: cfg } = useReportConfig();
  const save = useSaveReportConfig();

  const [markets, setMarkets] = useState<string[]>([]);
  const [schedule, setSchedule] = useState<Record<string, string>>({});
  const [threshold, setThreshold] = useState("5");
  const [detail, setDetail] = useState("STANDARD");
  const [tone, setTone] = useState("NEUTRAL");
  const [language, setLanguage] = useState("zh");
  const [focus, setFocus] = useState("");
  const [constraints, setConstraints] = useState("");
  const [providerId, setProviderId] = useState<number | null>(null);
  const [modelName, setModelName] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!cfg) return;
    setMarkets(cfg.enabled_markets ?? []);
    setSchedule(cfg.schedule ?? {});
    setThreshold(cfg.move_threshold_pct ?? "5");
    setDetail(cfg.detail_level ?? "STANDARD");
    setTone(cfg.tone ?? "NEUTRAL");
    setLanguage(cfg.language ?? "zh");
    setFocus(cfg.focus_text ?? "");
    setConstraints((cfg.constraints ?? []).join("\n"));
    setProviderId(cfg.provider_id ?? null);
    setModelName(cfg.model_name ?? null);
  }, [cfg]);

  const toggleMarket = (m: string) => {
    setMarkets((prev) => {
      if (prev.includes(m)) return prev.filter((x) => x !== m);
      setSchedule((s) => ({ ...s, [m]: s[m] || DEFAULT_TIME[m] }));
      return [...prev, m];
    });
  };

  const onSave = () => {
    setSaved(false);
    save.mutate(
      {
        enabled_markets: markets,
        schedule,
        move_threshold_pct: threshold,
        detail_level: detail,
        tone,
        language,
        focus_text: focus,
        constraints: constraints.split("\n").map((s) => s.trim()).filter(Boolean),
        provider_id: providerId,
        model_name: modelName,
      },
      { onSuccess: () => setSaved(true) },
    );
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Link href="/insights" className="inline-flex items-center gap-1.5 text-meta text-tertiary hover:text-primary">
        <ArrowLeft className="h-4 w-4" /> {t("insights.back")}
      </Link>
      <div>
        <h1 className="text-h1 text-primary">{t("config.title")}</h1>
        <p className="text-small text-secondary">{t("config.subtitle")}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("config.enabledMarkets")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {MARKETS.map((m) => (
              <Button
                key={m}
                size="sm"
                variant={markets.includes(m) ? "default" : "outline"}
                onClick={() => toggleMarket(m)}
              >
                {m}
              </Button>
            ))}
          </div>

          {/* 各市场时间 */}
          {markets.length > 0 && (
            <div className="space-y-2">
              <Label>{t("config.schedule")}</Label>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {markets.map((m) => (
                  <div key={m} className="flex items-center gap-1.5">
                    <span className="w-8 text-meta text-tertiary">{m}</span>
                    <Input
                      type="time"
                      className="tnum"
                      value={schedule[m] || DEFAULT_TIME[m]}
                      onChange={(e) => setSchedule((s) => ({ ...s, [m]: e.target.value }))}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("config.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <Label>{t("config.moveThreshold")}</Label>
            <Input
              type="number"
              className="tnum w-28"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>

          <Row label={t("config.detailLevel")}>
            {["BRIEF", "STANDARD", "DETAILED"].map((d) => (
              <Button key={d} size="sm" variant={detail === d ? "default" : "outline"} onClick={() => setDetail(d)}>
                {t(`config.detail.${d}`)}
              </Button>
            ))}
          </Row>

          <Row label={t("config.tone")}>
            {["CONSERVATIVE", "NEUTRAL"].map((tn) => (
              <Button key={tn} size="sm" variant={tone === tn ? "default" : "outline"} onClick={() => setTone(tn)}>
                {t(`config.tone.${tn}`)}
              </Button>
            ))}
          </Row>

          <Row label={t("config.language")}>
            {[
              { v: "zh", l: "中文" },
              { v: "ja", l: "日本語" },
              { v: "en", l: "EN" },
            ].map((o) => (
              <Button key={o.v} size="sm" variant={language === o.v ? "default" : "outline"} onClick={() => setLanguage(o.v)}>
                {o.l}
              </Button>
            ))}
          </Row>

          <Row label={t("config.aiModel")}>
            <ProviderModelPicker
              providerId={providerId}
              model={modelName}
              onChange={(pid, m) => {
                setProviderId(pid);
                setModelName(m);
              }}
            />
          </Row>

          <div className="space-y-1">
            <Label>{t("config.focusText")}</Label>
            <Input value={focus} onChange={(e) => setFocus(e.target.value)} placeholder={t("config.focusPlaceholder")} />
          </div>

          <div className="space-y-1">
            <Label>{t("config.constraints")}</Label>
            <Textarea
              rows={4}
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
              placeholder={t("config.constraintsPlaceholder")}
            />
          </div>

          <div className="flex items-center gap-3">
            <Button disabled={save.isPending} onClick={onSave}>
              {save.isPending ? t("config.saving") : t("config.save")}
            </Button>
            {saved && <span className="text-meta text-up">{t("config.saved")}</span>}
          </div>
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
