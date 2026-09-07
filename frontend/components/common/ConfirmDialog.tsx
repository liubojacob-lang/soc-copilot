"use client";

import { ReactNode } from "react";
import { AlertTriangle, Info } from "lucide-react";
import { Modal } from "./Modal";
import { Button } from "./Button";
import { cn } from "@/lib/utils";

interface ConfirmDialogProps {
  open: boolean;
  title: ReactNode;
  description?: ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: "danger" | "default";
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * 统一的确认弹窗，替换原生 confirm()。
 *
 * - 基于 Modal：Esc 关闭、遮罩点击关闭、焦点陷阱、滚动锁定、portal 渲染
 * - danger 变体：红色警告图标 + danger 按钮（删除等危险操作）
 * - default 变体：蓝色信息图标 + primary 按钮（普通确认）
 * - loading 时禁用关闭与按钮，防止重复提交
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmText = "Confirm",
  cancelText = "Cancel",
  variant = "danger",
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const isDanger = variant === "danger";

  return (
    <Modal
      open={open}
      onClose={loading ? () => {} : onCancel}
      size="sm"
      showCloseButton={false}
      closeOnOverlayClick={!loading}
      ariaLabel={typeof title === "string" ? title : undefined}
    >
      <div className="flex flex-col items-center text-center pt-2">
        <div
          className={cn(
            "w-11 h-11 rounded-full flex items-center justify-center mb-3.5 border",
            isDanger
              ? "bg-red-500/10 text-red-600 border-red-500/20 dark:text-red-400"
              : "bg-accent-500/10 text-accent-600 border-accent-500/20 dark:text-accent-400"
          )}
        >
          {isDanger ? (
            <AlertTriangle className="w-5 h-5" aria-hidden="true" />
          ) : (
            <Info className="w-5 h-5" aria-hidden="true" />
          )}
        </div>

        <h3 className="text-base font-semibold text-text-primary mb-1.5">{title}</h3>

        {description && (
          <div className="text-xs text-text-secondary leading-relaxed max-w-xs">{description}</div>
        )}
      </div>

      <div className="flex gap-3 mt-6">
        <Button
          type="button"
          variant="secondary"
          className="flex-1"
          onClick={onCancel}
          disabled={loading}
        >
          {cancelText}
        </Button>
        <Button
          type="button"
          variant={isDanger ? "danger" : "primary"}
          className="flex-1"
          onClick={onConfirm}
          isLoading={loading}
        >
          {confirmText}
        </Button>
      </div>
    </Modal>
  );
}

export type { ConfirmDialogProps };
