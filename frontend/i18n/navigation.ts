import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

/**
 * Locale-aware navigation APIs.
 *
 * All internal navigation MUST use these instead of `next/link` /
 * `next/navigation` — they keep the current locale prefix on every URL
 * and support `{ locale }` to switch languages in place.
 */
export const { Link, redirect, permanentRedirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
