'use client';

import { ReactNode } from "react";
import { GlobalSearch } from "@/components/GlobalSearch";
import { ToastProvider } from "@/components/Toast";
import { SkipToContent } from "@/components/common";
import { QueryProvider } from "./providers/QueryProvider";

export function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <QueryProvider enableDevtools={process.env.NODE_ENV === 'development'}>
      <ToastProvider>
        <SkipToContent />
        {children}
        <GlobalSearch />
      </ToastProvider>
    </QueryProvider>
  );
}
