"use client";

import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/use-t";

export default function Error({ error, reset }: { error: Error; reset: () => void }) {
  const { t } = useT();
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 py-24">
      <h1 className="text-h1 text-primary">{t("error.title")}</h1>
      <p className="max-w-md text-center text-small text-secondary">{error.message || t("error.unknown")}</p>
      <Button onClick={reset}>{t("error.retry")}</Button>
    </div>
  );
}
