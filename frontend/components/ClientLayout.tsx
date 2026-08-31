"use client";

import { ReactNode } from "react";
import { usePathname } from "@/i18n/navigation";
import Navigation from "@/components/Navigation";
import { GlobalSearch } from "@/components/GlobalSearch";
import { ToastProvider } from "@/components/Toast";
import { SkipToContent } from "@/components/common";
import { QueryProvider } from "./providers/QueryProvider";

/** Paths that render without the global navigation shell. */
const NAV_EXCLUDED_SUFFIXES = ["/login"];

export function ClientLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "";
  const hideNav = NAV_EXCLUDED_SUFFIXES.some((suffix) => pathname.endsWith(suffix));

  return (
    <QueryProvider enableDevtools={process.env.NODE_ENV === "development"}>
      <ToastProvider>
        <SkipToContent />
        {!hideNav && <Navigation />}
        {children}
        <GlobalSearch />
      </ToastProvider>
    </QueryProvider>
  );
}
