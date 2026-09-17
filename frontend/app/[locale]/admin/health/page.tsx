"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";
import { LoadingSpinner } from "@/components/common";

/**
 * Legacy Admin Health Page
 *
 * System health metrics have been consolidated into the comprehensive
 * System Monitor (`/admin/dashboard`). Requests to this route are seamlessly
 * redirected to the unified monitoring page.
 */
export default function AdminHealthRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/admin/dashboard");
  }, [router]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
      <LoadingSpinner size="lg" color="soc" label="Redirecting to System Monitor..." />
    </div>
  );
}
