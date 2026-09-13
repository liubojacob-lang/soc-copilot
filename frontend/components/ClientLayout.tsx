"use client";

import { useState, useEffect, type ReactNode } from "react";
import { usePathname } from "@/i18n/navigation";

import Navigation from "@/components/Navigation";
import { Sidebar, MobileNavDrawer } from "@/components/layout/Sidebar";
import { GlobalSearch } from "@/components/GlobalSearch";
import { ToastProvider } from "@/components/Toast";
import { SkipToContent } from "@/components/common";
import { QueryProvider } from "./providers/QueryProvider";
import { HeaderProvider } from "./providers/HeaderProvider";
import { cn } from "@/lib/utils";

/** Paths that render without the global shell. */
const NAV_EXCLUDED_SUFFIXES = ["/login"];

interface ClientLayoutProps {
  children: ReactNode;
  initialRole?: string | null;
  initialSidebarCollapsed?: boolean;
  initialCollapsedGroups?: string[];
}

export function ClientLayout({
  children,
  initialRole = null,
  initialSidebarCollapsed = false,
  initialCollapsedGroups = [],
}: ClientLayoutProps) {
  const pathname = usePathname() ?? "";
  const hideNav = NAV_EXCLUDED_SUFFIXES.some((suffix) => pathname.endsWith(suffix));
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  if (hideNav) {
    return (
      <QueryProvider enableDevtools={process.env.NODE_ENV === "development"}>
        <ToastProvider>
          <main id="main-content">{children}</main>
          <GlobalSearch />
        </ToastProvider>
      </QueryProvider>
    );
  }

  return (
    <QueryProvider enableDevtools={process.env.NODE_ENV === "development"}>
      <ToastProvider>
        <HeaderProvider>
          <SkipToContent />
          <Sidebar
            initialRole={initialRole}
            initialCollapsed={initialSidebarCollapsed}
            initialCollapsedGroups={initialCollapsedGroups}
          />
          <MobileNavDrawer
            isOpen={mobileNavOpen}
            onClose={() => setMobileNavOpen(false)}
            initialRole={initialRole}
            initialCollapsedGroups={initialCollapsedGroups}
          />
          {/* 内容区左 padding 跟随 --sidebar-w：展开 240px / 折叠 64px / 移动端 0。
              首屏加载前禁用 transition，避免从默认 padding 动画滑入引起抖动 */}
          <div
            className={cn(
              "flex min-h-screen flex-col",
              isMounted && "transition-[padding] duration-200"
            )}
            style={{ paddingLeft: "var(--sidebar-w)" }}
          >
            <Navigation onOpenMobileNav={() => setMobileNavOpen(true)} />
            <main id="main-content" className="flex-1">
              {children}
            </main>
          </div>
          <GlobalSearch />
        </HeaderProvider>
      </ToastProvider>
    </QueryProvider>
  );
}
