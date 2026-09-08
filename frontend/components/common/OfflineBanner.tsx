"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { WifiOff } from "lucide-react";

/** Global network-status banner: tells the user why actions are failing. */
export function OfflineBanner() {
  const t = useTranslations("common");
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (!offline) return null;

  return (
    <div
      role="alert"
      className="sticky top-0 z-50 bg-amber-500/95 text-amber-950 text-sm font-medium px-4 py-2 text-center flex items-center justify-center gap-2"
    >
      <WifiOff className="w-4 h-4 shrink-0" />
      <span>{t("offlineBanner")}</span>
    </div>
  );
}
