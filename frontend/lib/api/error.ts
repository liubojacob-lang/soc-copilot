// Error handling utilities
import { ApiError } from "./client";

export interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Array<{
      field: string;
      message: string;
    }>;
  };
  metadata: {
    request_id: string;
    timestamp: string;
  };
}

export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  metadata: {
    request_id: string;
    timestamp: string;
    pagination?: {
      page: number;
      page_size: number;
      total: number;
    };
  };
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

export function handleApiError(error: any): string {
  if (error instanceof ApiError) {
    try {
      const errorData = JSON.parse(error.message);
      if (errorData.error) {
        return errorData.error.message || `API Error: ${error.status}`;
      }
    } catch {
      // If error message is not JSON
    }
    return `API Error: ${error.status} - ${error.message}`;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unknown error occurred";
}

export function isApiError(response: any): response is ApiErrorResponse {
  return response && typeof response === "object" && response.success === false && response.error;
}

export function isApiSuccess<T>(response: any): response is ApiSuccessResponse<T> {
  return response && typeof response === "object" && response.success === true && response.data;
}
