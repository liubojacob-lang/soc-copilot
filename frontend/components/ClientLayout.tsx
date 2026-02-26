'use client';

import { ReactNode } from "react";
import { GlobalSearch } from "@/components/GlobalSearch";
import { ToastProvider } from "@/components/Toast";

export function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      {children}
      <GlobalSearch />
    </ToastProvider>
  );
}
