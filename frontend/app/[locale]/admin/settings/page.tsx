"use client";

import { useEffect } from "react";
import { useRouter } from "@/i18n/navigation";

/**
 * System settings now live inside the unified settings centre.
 *
 * This route is kept as a compatibility shim for existing bookmarks and for
 * links embedded in older documentation.
 */
export default function AdminSettingsRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/settings/system");
  }, [router]);

  return null;
}
