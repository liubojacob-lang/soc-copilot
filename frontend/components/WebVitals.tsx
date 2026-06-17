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

  if (navigator.sendBeacon) {
    const body = JSON.stringify({
      name: metric.name,
      value: metric.value,
      rating: metric.rating,
      id: metric.id,
      page: window.location.pathname,
    });
    navigator.sendBeacon("/api/analytics/vitals", body);
  }
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
