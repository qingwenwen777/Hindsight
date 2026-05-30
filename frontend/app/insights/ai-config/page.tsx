"use client";

import { Check, Eye, EyeOff, Loader2, Plus, RefreshCw, Star, Trash2, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  useAiProviders,
  useCreateProvider,
  useDeleteProvider,
  useFetchModels,
  useSetDefaultProvider,
  useTestConnection,
  useUpdateProvider,
  type AiProvider,
} from "@/lib/hooks/use-ai-providers";
import { useT } from "@/lib/i18n/use-t";
import { cn } from "@/lib/utils";

const PROTOCOLS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
];

export default function AiConfigPage() {
  const { t } = useT();
  const { data: providers } = useAiProviders();
  const createProvider = useCreateProvider();
  const setDefault = useSetDefaultProvider();

  const [activeId, setActiveId] = useState<number | null>(null);
  const active = (providers ?? []).find((p) => p.id === activeId) ?? null;

  // 默认选中第一个
  useEffect(() => {
    if (activeId == null && providers && providers.length > 0) {
      setActiveId(providers[0].id);
    }
  }, [providers, activeId]);

  const addProvider = async () => {
    const created = await createProvider.mutateAsync({
      name: t("aicfg.newProviderName"),
      protocol: "openai",
      base_url: "",
      api_key: "",
      models: [],
    });
    setActiveId(created.id);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-h1 text-primary">{t("aicfg.title")}</h1>
        <p className="text-small text-secondary">{t("aicfg.subtitle")}</p>
      </div>

      <div className="flex gap-6">
        {/* 左侧：服务商列表 */}
        <aside className="w-56 shrink-0">
          <div className="grid gap-1">
            {(providers ?? []).map((p) => (
              <button
                key={p.id}
                onClick={() => setActiveId(p.id)}
                className={cn(
                  "group flex items-center gap-2 rounded-lg px-3 py-2.5 text-left transition-colors",
                  p.id === activeId
                    ? "bg-elevated text-primary"
                    : "text-tertiary hover:bg-elevated/60 hover:text-primary",
                )}
              >
                <span className="min-w-0 flex-1 truncate text-body">{p.name}</span>
                {p.is_default && <Star className="h-3.5 w-3.5 shrink-0 fill-amber-400 text-amber-400" />}
                {p.enabled && (
                  <span className="shrink-0 rounded-full bg-up/15 px-1.5 text-[10px] font-medium text-up">
                    ON
                  </span>
                )}
              </button>
            ))}
          </div>
          <Button
            variant="outline"
            className="mt-3 w-full gap-1.5"
            onClick={addProvider}
            disabled={createProvider.isPending}
          >
            <Plus className="h-4 w-4" />
            {t("aicfg.add")}
          </Button>
        </aside>

        {/* 右侧：详情编辑 */}
        <div className="min-w-0 flex-1">
          {active ? (
            <ProviderEditor
              key={active.id}
              provider={active}
              onSetDefault={() => setDefault.mutate(active.id)}
            />
          ) : (
            <div className="flex h-64 items-center justify-center rounded-card border border-dashed border-border-default text-tertiary">
              {t("aicfg.empty")}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ProviderEditor({
  provider,
  onSetDefault,
}: {
  provider: AiProvider;
  onSetDefault: () => void;
}) {
  const { t } = useT();
  const update = useUpdateProvider();
  const del = useDeleteProvider();
  const fetchModels = useFetchModels();
  const testConn = useTestConnection();

  const [name, setName] = useState(provider.name);
  const [protocol, setProtocol] = useState(provider.protocol);
  const [baseUrl, setBaseUrl] = useState(provider.base_url);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [models, setModels] = useState<string[]>(provider.models);
  const [defaultModel, setDefaultModel] = useState(provider.default_model ?? "");
  const [enabled, setEnabled] = useState(provider.enabled);
  const [newModel, setNewModel] = useState("");
  const [savedFlash, setSavedFlash] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);

  const persist = (extra: Record<string, unknown> = {}) => {
    update.mutate(
      {
        id: provider.id,
        name,
        protocol,
        base_url: baseUrl,
        models,
        default_model: defaultModel || null,
        enabled,
        ...(apiKey ? { api_key: apiKey } : {}),
        ...extra,
      },
      {
        onSuccess: () => {
          setSavedFlash(true);
          setApiKey("");
          setTimeout(() => setSavedFlash(false), 1500);
        },
      },
    );
  };

  const probeBody = () => ({
    provider_id: provider.id,
    protocol,
    base_url: baseUrl,
    ...(apiKey ? { api_key: apiKey } : {}),
  });

  const onFetchModels = async () => {
    setTestResult(null);
    try {
      const res = await fetchModels.mutateAsync(probeBody());
      // 合并去重
      setModels((prev) => Array.from(new Set([...prev, ...res.models])));
    } catch (e) {
      setTestResult({ ok: false, message: (e as Error).message });
    }
  };

  const onTest = async () => {
    setTestResult(null);
    const model = defaultModel || models[0];
    try {
      const res = await testConn.mutateAsync({ ...probeBody(), model });
      setTestResult(res);
    } catch (e) {
      setTestResult({ ok: false, message: (e as Error).message });
    }
  };

  const removeModel = (m: string) => {
    setModels((prev) => prev.filter((x) => x !== m));
    if (defaultModel === m) setDefaultModel("");
  };

  const addModel = () => {
    const m = newModel.trim();
    if (!m) return;
    setModels((prev) => (prev.includes(m) ? prev : [...prev, m]));
    if (!defaultModel) setDefaultModel(m);
    setNewModel("");
  };

  return (
    <div className="space-y-6 rounded-card border border-border-default bg-surface p-6">
      {/* 头部：名称 + 启用开关 + 默认 + 删除 */}
      <div className="flex items-center justify-between gap-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => persist()}
          className="min-w-0 flex-1 bg-transparent text-title font-medium text-primary outline-none"
        />
        <div className="flex items-center gap-3">
          {!provider.is_default && (
            <Button size="sm" variant="outline" className="gap-1.5" onClick={onSetDefault}>
              <Star className="h-3.5 w-3.5" />
              {t("aicfg.setDefault")}
            </Button>
          )}
          {provider.is_default && (
            <span className="inline-flex items-center gap-1 rounded-md bg-amber-400/15 px-2 py-1 text-caption font-medium text-amber-500">
              <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
              {t("aicfg.default")}
            </span>
          )}
          <button
            onClick={() => {
              setEnabled((v) => {
                const nv = !v;
                persist({ enabled: nv });
                return nv;
              });
            }}
            className={cn(
              "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors",
              enabled ? "bg-up" : "bg-border-strong",
            )}
            aria-label={t("aicfg.enabled")}
          >
            <span
              className={cn(
                "inline-block h-5 w-5 rounded-full bg-white shadow-md ring-1 ring-black/10 transition-transform",
                enabled ? "translate-x-[22px]" : "translate-x-0.5",
              )}
            />
          </button>
          <button
            onClick={() => del.mutate(provider.id)}
            className="flex h-8 w-8 items-center justify-center rounded-md text-tertiary hover:bg-elevated hover:text-danger"
            aria-label={t("aicfg.delete")}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* 协议 */}
      <div className="space-y-1.5">
        <Label>{t("aicfg.protocol")}</Label>
        <div className="flex gap-2">
          {PROTOCOLS.map((p) => (
            <Button
              key={p.value}
              size="sm"
              variant={protocol === p.value ? "default" : "outline"}
              onClick={() => setProtocol(p.value as "openai" | "anthropic")}
            >
              {p.label}
            </Button>
          ))}
        </div>
        <p className="text-caption text-tertiary">{t("aicfg.protocolHint")}</p>
      </div>

      {/* API 密钥 */}
      <div className="space-y-1.5">
        <Label>{t("aicfg.apiKey")}</Label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Input
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              onBlur={() => apiKey && persist()}
              placeholder={provider.has_key ? provider.api_key_mask : t("aicfg.apiKeyPlaceholder")}
              className="pr-9"
            />
            <button
              onClick={() => setShowKey((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-tertiary hover:text-primary"
              type="button"
            >
              {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <Button variant="outline" className="gap-1.5" onClick={onTest} disabled={testConn.isPending}>
            {testConn.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
            {t("aicfg.test")}
          </Button>
        </div>
        {testResult && (
          <p className={cn("text-caption", testResult.ok ? "text-up" : "text-danger")}>
            {testResult.ok ? t("aicfg.testOk") : t("aicfg.testFail")}
            {testResult.message ? `：${testResult.message}` : ""}
          </p>
        )}
      </div>

      {/* API 地址 */}
      <div className="space-y-1.5">
        <Label>{t("aicfg.baseUrl")}</Label>
        <Input
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          onBlur={() => persist()}
          placeholder={protocol === "anthropic" ? "https://api.anthropic.com" : "https://api.openai.com/v1"}
        />
        <p className="text-caption text-tertiary">
          {t("aicfg.baseUrlHint", {
            ex:
              protocol === "anthropic"
                ? `${baseUrl || "https://api.anthropic.com"}/v1/messages`
                : `${baseUrl || "https://api.openai.com/v1"}/chat/completions`,
          })}
        </p>
      </div>

      {/* 模型 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>
            {t("aicfg.models")} <span className="text-tertiary">{models.length}</span>
          </Label>
          <Button variant="outline" size="sm" className="gap-1.5" onClick={onFetchModels} disabled={fetchModels.isPending}>
            {fetchModels.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            {t("aicfg.fetchModels")}
          </Button>
        </div>

        {/* 手动添加 */}
        <div className="flex gap-2">
          <Input
            value={newModel}
            onChange={(e) => setNewModel(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addModel()}
            placeholder={t("aicfg.modelPlaceholder")}
          />
          <Button variant="secondary" onClick={addModel} className="shrink-0 gap-1.5">
            <Plus className="h-4 w-4" />
            {t("aicfg.addModel")}
          </Button>
        </div>

        {models.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border-default px-3 py-6 text-center text-caption text-tertiary">
            {t("aicfg.noModels")}
          </p>
        ) : (
          <div className="grid gap-1">
            {models.map((m) => {
              const isDefault = defaultModel === m;
              return (
                <div
                  key={m}
                  className="group flex items-center gap-2 rounded-md border border-border-default px-3 py-1.5 hover:border-border-strong"
                >
                  <span className="min-w-0 flex-1 truncate text-small text-primary">{m}</span>
                  <button
                    onClick={() => setDefaultModel(m)}
                    className={cn(
                      "inline-flex items-center gap-1 rounded px-1 py-0.5 text-caption transition-colors",
                      isDefault ? "text-amber-500" : "text-tertiary opacity-0 group-hover:opacity-100 hover:text-primary",
                    )}
                    title={t("aicfg.setDefaultModel")}
                  >
                    <Star className={cn("h-3 w-3", isDefault && "fill-amber-400 text-amber-400")} />
                    {isDefault && t("aicfg.defaultModel")}
                  </button>
                  <button
                    onClick={() => removeModel(m)}
                    className="flex h-5 w-5 items-center justify-center rounded text-tertiary opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* 保存 */}
      <div className="flex items-center gap-3 border-t border-border-default pt-4">
        <Button onClick={() => persist()} disabled={update.isPending} className="gap-1.5">
          {update.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
          {t("aicfg.save")}
        </Button>
        {savedFlash && <span className="text-meta text-up">{t("aicfg.saved")}</span>}
      </div>
    </div>
  );
}
