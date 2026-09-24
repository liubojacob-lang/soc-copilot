"use client";

import { ReactNode, useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useFocusTrap } from "@/hooks/useFocusTrap";

/**
 * 统一的 Modal 弹框组件。
 *
 * 解决各页面手写弹框的共性问题:
 * - 居中对齐 + 响应式(移动端底部抽屉 / 桌面居中)
 * - 内容超高自动滚动(max-h 90vh),按钮始终可见
 * - z-50 层级,不被遮挡
 * - ESC 关闭 + 点击遮罩关闭 + 焦点陷阱
 * - 无障碍属性(role/aria-modal/aria-label)
 * - 可选 header(title + 关闭按钮) / footer(按钮区) 分区
 *
 * 复用 globals.css 的 .modal-responsive / .modal-content-responsive。
 */
interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  /** 自定义关闭按钮 aria-label */
  closeButtonLabel?: string;
  /** 内容区额外 class */
  contentClassName?: string;
  /** 弹框最大宽度,默认 md */
  size?: "sm" | "md" | "lg" | "xl";
  /** 是否显示右上角关闭按钮,默认 true */
  showCloseButton?: boolean;
  /** 点击遮罩是否关闭,默认 true */
  closeOnOverlayClick?: boolean;
  /** 底部按钮区(通常放取消/确认按钮) */
  footer?: ReactNode;
  /** 自定义 aria-label */
  ariaLabel?: string;
  children: ReactNode;
}

const SIZE_MAP: Record<NonNullable<ModalProps["size"]>, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-2xl",
};

export function Modal({
  open,
  onClose,
  title,
  closeButtonLabel = "Close",
  contentClassName,
  size = "md",
  showCloseButton = true,
  closeOnOverlayClick = true,
  footer,
  ariaLabel,
  children,
}: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const titleId = useId();

  // Focus trap: save/restore focus, Tab cycling, Escape close
  useFocusTrap(open, onClose, contentRef);

  // Lock body scroll when open
  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [open]);

  if (!open || typeof document === "undefined") return null;

  const resolvedAriaLabel = ariaLabel || (typeof title === "string" ? title : undefined);
  const ariaLabelledBy = resolvedAriaLabel ? undefined : title ? titleId : undefined;

  const overlay = (
    <div
      className="modal-responsive bg-black/50 dark:bg-black/70"
      role="dialog"
      aria-modal="true"
      aria-label={resolvedAriaLabel}
      aria-labelledby={ariaLabelledBy}
      onMouseDown={(e) => {
        // 仅点击遮罩本身(非内容)时关闭
        if (closeOnOverlayClick && e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={contentRef}
        className={cn(
          "modal-content-responsive",
          // 覆盖默认 max-w-lg,按 size 调整
          "max-w-lg-none",
          SIZE_MAP[size],
          "flex flex-col",
          contentClassName
        )}
        // 阻止 mousedown 冒泡到遮罩(避免误关闭)
        onMouseDown={(e) => e.stopPropagation()}
        tabIndex={-1}
      >
        {(title || showCloseButton) && (
          <div className="flex items-center justify-between gap-4 px-6 pt-5 pb-3 border-b border-gray-200 dark:border-gray-700 shrink-0">
            <h2
              id={titleId}
              className="text-lg font-semibold text-gray-900 dark:text-white truncate"
            >
              {title}
            </h2>
            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                aria-label={closeButtonLabel}
                className="shrink-0 p-1.5 rounded-md text-text-tertiary hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 dark:hover:text-gray-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>

        {footer && (
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );

  return createPortal(overlay, document.body);
}
