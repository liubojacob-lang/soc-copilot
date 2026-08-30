import type { MetadataRoute } from "next";

import { getMetadataBase } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  const base = getMetadataBase();

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", "/*?*token="],
    },
    sitemap: new URL("/sitemap.xml", base).toString(),
  };
}
