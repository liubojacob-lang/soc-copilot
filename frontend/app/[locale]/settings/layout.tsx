import type { ReactNode } from "react";

/**
 * Shared shell for every settings route.
 *
 * Navigation between settings sections is handled by the global sidebar —
 * there is no secondary sidebar here to avoid a nested double-sidebar layout.
 */
export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-surface-page dark:bg-gray-950 transition-colors">
      {children}
    </div>
  );
}
