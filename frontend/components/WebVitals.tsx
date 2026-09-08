"use client";

import { useEffect } from "react";
import { onCLS, onINP, onLCP, onFCP, onTTFB, type Metric } from "web-vitals";

type WebVitalsMetric = Metric & {
  rating: "good" | "needs-improvement" | "poor";
};

function sendToAnalytics(metric: WebVitalsMetric) {
  if (process.env.NODE_ENV === "development") {
    return;
  }

  // Only report when a vitals ingestion endpoint is configured; the backend
  // has no /api/analytics/vitals handler today, so reporting would only
  // generate failed beacon requests on every page load.
  const endpoint = process.env.NEXT_PUBLIC_VITALS_ENDPOINT;
  if (!endpoint || !navigator.sendBeacon) {
    return;
  }

  const body = JSON.stringify({
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    id: metric.id,
    page: window.location.pathname,
  });
  navigator.sendBeacon(endpoint, body);
}

export function WebVitals() {
  useEffect(() => {
    onCLS(sendToAnalytics);
    onINP(sendToAnalytics);
    onLCP(sendToAnalytics);
    onFCP(sendToAnalytics);
    onTTFB(sendToAnalytics);
  }, []);

  return null;
}
