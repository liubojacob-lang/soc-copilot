"use client";

import { useRouter } from "@/i18n/navigation";
import { useTranslations } from "next-intl";
import { loadAuthState, logout } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { AuditPageContainer } from "./components/AuditPageContainer";
import { useEffect, useState } from "react";

export default function AuditLogsPage() {
  const router = useRouter();
  const t = useTranslations("adminAudit");
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const authState = await loadAuthState();

      if (!authState) {
        router.push("/login");
        return;
      }

      // Auditor / admin / analyst 都可查看审计日志（后端按 auditor 放行）
      const role = authState.user?.role;
      if (role !== "admin" && role !== "analyst" && role !== "auditor") {
        router.push("/");
        return;
      }

      setIsAuthorized(true);
      setLoading(false);
    };

    checkAuth();
  }, [router]);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-page overflow-x-hidden">
        <PageHeader title="Audit Logs" />
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-8 bg-border-subtle rounded w-1/4 mb-4"></div>
            <div className="h-4 bg-border-subtle rounded w-1/2 mb-8"></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              {[1, 2, 3].map((i) => (
                <div key={i} className="bg-surface-card rounded-lg shadow p-6">
                  <div className="h-4 bg-border-subtle rounded w-1/3 mb-2"></div>
                  <div className="h-8 bg-border-subtle rounded w-1/2"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return null;
  }

  return (
    <div className="min-h-screen bg-surface-page overflow-x-hidden">
      <PageHeader title={t("title")} subtitle={t("subtitle")} />
      <AuditPageContainer />
    </div>
  );
}
