// Base API client with common utilities
import { getAuthHeaders } from "./auth";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = "") {
    this.baseUrl = baseUrl;
  }

  async request<T>(path: string, options: RequestInit = {}, timeoutMs: number = 30000): Promise<T> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const urlWithBust = path.includes("?")
        ? `${this.baseUrl}${path}&_t=${Date.now()}`
        : `${this.baseUrl}${path}?_t=${Date.now()}`;

      const response = await fetch(urlWithBust, {
        ...options,
        signal: controller.signal,
        keepalive: true,
        headers: {
          ...getAuthHeaders(),
          ...options.headers,
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const error = await response.text();
        throw new ApiError(response.status, error || "Request failed");
      }

      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === "AbortError") {
        throw new Error(`Request timeout after ${timeoutMs / 1000}s`);
      }
      throw error;
    }
  }

  async get<T>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, {
      method: "GET",
      ...options,
    });
  }

  async post<T>(path: string, data: Record<string, any> = {}, timeoutMs?: number): Promise<T> {
    return this.request<T>(
      path,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
      },
      timeoutMs
    );
  }

  async put<T>(path: string, data: Record<string, any> = {}): Promise<T> {
    return this.request<T>(path, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
  }

  async patch<T>(path: string, data: Record<string, any> = {}): Promise<T> {
    return this.request<T>(path, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, {
      method: "DELETE",
    });
  }
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export const apiClient = new ApiClient("");
