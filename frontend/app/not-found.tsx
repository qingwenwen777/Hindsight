"use client";

import Link from "next/link";

import { useT } from "@/lib/i18n/use-t";

export default function NotFound() {
  const { t } = useT();
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 py-24">
      <h1 className="text-display text-primary">404</h1>
      <p className="text-small text-secondary">{t("notFound.desc")}</p>
      <Link
        href="/"
        className="rounded-md bg-btn-primary px-4 py-2 text-small font-medium text-btn-primary-fg transition-opacity hover:opacity-90"
      >
        {t("notFound.backHome")}
      </Link>
    </div>
  );
}
