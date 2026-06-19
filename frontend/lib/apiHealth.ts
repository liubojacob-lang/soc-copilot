/**
 * API Health Check Module
 * 提供API健康状态监控和降级功能
 */

// API健康状态
export type ApiHealthStatus = "unknown" | "degraded" | "healthy";

let currentHealthStatus: ApiHealthStatus = "unknown";

// API基础URL配置
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

/**
 * 执行API健康检查
 * @returns Promise<void>
 */
export async function checkApiHealth(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/health`, {
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
