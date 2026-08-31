/**
 * API Health Check Module
 * 提供API健康状态监控和降级功能
 */

// API健康状态
export type ApiHealthStatus = "unknown" | "degraded" | "healthy";

let currentHealthStatus: ApiHealthStatus = "unknown";

/**
 * 执行API健康检查
 * @returns Promise<void>
 */
export async function checkApiHealth(): Promise<void> {
  try {
    // 同源路径：dev 由 next.config rewrite 转发，prod 由 nginx 转发
    const response = await fetch("/api/v1/health", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
      // 5秒超时
      signal: AbortSignal.timeout(5000),
    });

    if ((response as any)?.status === 200) {
      currentHealthStatus = "healthy";
    } else {
      currentHealthStatus = "degraded";
      console.warn("[API] Backend health check failed, running in degraded mode");
    }
  } catch (error) {
    currentHealthStatus = "degraded";
    console.error("[API] Health check failed:", error);
  }
}

/**
 * 获取当前API健康状态
 * @returns 当前健康状态
 */
export function getApiHealthStatus(): ApiHealthStatus {
  return currentHealthStatus;
}

/**
 * 初始化健康检查（模块加载时执行一次）
 */
export function initHealthCheck(): void {
  if (typeof window !== "undefined") {
    checkApiHealth();

    // 定期健康检查（每30秒）
    setInterval(() => {
      checkApiHealth();
    }, 30000);
  }
}
