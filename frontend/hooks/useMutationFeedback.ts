"use client";

import { useCallback } from "react";
import { useToast } from "@/components/Toast";

/**
 * 统一的操作反馈 hook。
 *
 * 封装 mutation/异步操作的 toast 反馈，解决删除/变更操作零反馈问题：
 * - notifySuccess: 成功提示（默认绿色 success toast）
 * - notifyError: 失败提示（默认红色 error toast，优先使用 Error 实例的 message）
 * - runWithFeedback: 执行异步操作并自动附带成功/失败 toast
 *
 * 与项目现有异步模式（authFetch/authFetchJSON + setError）兼容，
 * 可作为 React Query mutation 的 onSuccess/onError 反馈层。
 */
interface MutationFeedbackOptions {
  /** 默认成功提示文案（可被每次调用的 successMessage 覆盖） */
  successMessage?: string;
  /** 默认失败提示文案（Error.message 优先，可被每次调用的 errorMessage 覆盖） */
  errorMessage?: string;
}

export function useMutationFeedback(options: MutationFeedbackOptions = {}) {
  const { showToast } = useToast();

  const notifySuccess = useCallback(
    (message?: string) => {
      showToast(message || options.successMessage || "Operation completed", "success");
    },
    [showToast, options.successMessage]
  );

  const notifyError = useCallback(
    (error?: unknown, message?: string) => {
      const resolved =
        error instanceof Error && error.message
          ? error.message
          : message || options.errorMessage || "Operation failed";
      showToast(resolved, "error");
    },
    [showToast, options.errorMessage]
  );

  /**
   * 执行异步操作并自动反馈。
   * @param fn 要执行的异步操作（mutation / API 调用）
   * @param feedback 本次调用的提示文案覆盖
   * @returns 操作成功返回结果；失败返回 undefined（已 toast）
   */
  const runWithFeedback = useCallback(
    async <T>(
      fn: () => Promise<T>,
      feedback?: { successMessage?: string; errorMessage?: string }
    ): Promise<T | undefined> => {
      try {
        const result = await fn();
        notifySuccess(feedback?.successMessage);
        return result;
      } catch (error) {
        notifyError(error, feedback?.errorMessage);
        return undefined;
      }
    },
    [notifySuccess, notifyError]
  );

  return { notifySuccess, notifyError, runWithFeedback };
}

export type { MutationFeedbackOptions };
