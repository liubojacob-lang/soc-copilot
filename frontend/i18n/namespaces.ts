export const CORE_NAMESPACES = ["core"] as const;

export const ROUTE_NAMESPACES: Record<string, string[]> = {
  "/": ["home", "dashboard"],
  "/login": ["login"],
  "/alerts": ["alerts"],
  "/alerts/[id]": ["alerts", "playbooks"],
  "/playbooks": ["playbooks"],
  "/playbooks/definitions": ["playbooks"],
  "/playbooks/approvals": ["playbooks"],
  "/threat-intel": ["threat-intel"],
  "/threat-intel/dashboard": ["threat-intel"],
  "/ai-assistant": ["ai-assistant"],
  "/audit": ["audit"],
  "/admin": ["admin"],
  "/admin/dashboard": ["admin"],
  "/admin/users": ["admin", "users"],
  "/admin/settings": ["admin", "settings"],
  "/admin/audit": ["admin", "audit"],
  "/admin/secrets": ["admin"],
  "/admin/health": ["admin"],
  "/settings": ["settings"],
  "/settings/ai-models": ["settings", "aiModels"],
  "/settings/api-keys": ["settings", "apiKeys"],
  "/settings/notifications": ["settings"],
  "/users": ["users"],
  "/reports": ["reports"],
  "/ueba": ["ueba"],
  "/triggers": ["triggers"],
  "/triggers/webhook/new": ["triggers"],
  "/triggers/cron/new": ["triggers"],
  "/monitor": ["monitor"],
  "/marketplace": ["marketplace"],
  "/threat-hunting": ["threat-hunting"],
  "/assets": ["assets"],
  "/cloud-native": ["cloud-native"],
  "/correlation": ["correlation"],
} as const;

export const SHARED_NAMESPACES = ["analytics", "other"] as const;

export function getRequiredNamespaces(pathname: string): string[] {
  const core = [...CORE_NAMESPACES];

  let route: string[] = [];
  for (const [pattern, namespaces] of Object.entries(ROUTE_NAMESPACES)) {
    if (matchPath(pattern, pathname)) {
      route = [...namespaces];
      break;
    }
  }

  const shared = [...SHARED_NAMESPACES];

  return [...new Set([...core, ...route, ...shared])];
}

function matchPath(pattern: string, pathname: string): boolean {
  if (pattern === pathname) {
    return true;
  }

  if (pattern.includes("[") && pattern.includes("]")) {
    const regex = new RegExp("^" + pattern.replace(/\[[^\]]+\]/g, "[^/]+") + "$");
    return regex.test(pathname);
  }

  if (pathname.startsWith(pattern + "/")) {
    return true;
  }

  return false;
}

export type Namespace =
  | (typeof CORE_NAMESPACES)[number]
  | (typeof SHARED_NAMESPACES)[number]
  | keyof typeof ROUTE_NAMESPACES;
