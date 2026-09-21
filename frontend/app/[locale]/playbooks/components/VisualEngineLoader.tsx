"use client";

import { useTranslations } from "next-intl";

export function VisualEngineLoader() {
  const t = useTranslations("playbooks");
  return (
    <div className="h-[460px] w-full flex items-center justify-center bg-surface-hover/30 rounded-2xl border border-dashed border-border-subtle">
      <div className="flex items-center gap-2 text-text-tertiary text-xs">
        <div className="w-4 h-4 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
        <span>{t("loadingEngine")}</span>
      </div>
    </div>
  );
}

export default VisualEngineLoader;
