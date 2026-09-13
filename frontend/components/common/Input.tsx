"use client";

import {
  forwardRef,
  InputHTMLAttributes,
  TextareaHTMLAttributes,
  SelectHTMLAttributes,
  ReactNode,
} from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Input 组件变体配置
 */
const inputVariants = cva(
  "w-full rounded-md border bg-surface-input text-text-primary placeholder:text-text-disabled transition-all duration-150 focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation",
  {
    variants: {
      variant: {
        default:
          "border-border-default hover:border-border-strong focus:ring-2 focus:ring-accent-500/30 focus:border-accent-600 dark:focus:border-accent-400",
        error:
          "border-danger-500 text-danger-900 dark:text-danger-100 focus:ring-2 focus:ring-danger-500/30 focus:border-danger-600",
        success:
          "border-success-500 text-success-900 dark:text-success-100 focus:ring-2 focus:ring-success-500/30 focus:border-success-600",
      },
      size: {
        sm: "h-8 px-2.5 text-xs",
        md: "h-9 px-3 text-sm",
        lg: "h-10 px-3.5 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);

type InputVariant = VariantProps<typeof inputVariants>["variant"];
type InputSize = VariantProps<typeof inputVariants>["size"];

// ============================================================================
// Input Component
// ============================================================================

interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "size">, VariantProps<typeof inputVariants> {
  error?: string;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  label?: string;
  helperText?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    { className, variant, size, error, leftIcon, rightIcon, label, helperText, id, ...props },
    ref
  ) => {
    const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = !!error || variant === "error";
    const effectiveVariant = hasError ? "error" : variant;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
          >
            {label}
          </label>
        )}

        <div className="relative">
          {leftIcon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            className={cn(
              inputVariants({ variant: effectiveVariant, size }),
              leftIcon && "pl-10",
              rightIcon && "pr-10",
              className
            )}
            aria-invalid={hasError}
            {...props}
          />

          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500">
              {rightIcon}
            </div>
          )}
        </div>

        {error && <p className="mt-1.5 text-sm text-danger-600 dark:text-danger-400">{error}</p>}

        {helperText && !error && (
          <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

// ============================================================================
// Textarea Component
// ============================================================================

interface TextareaProps
  extends
    Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "size">,
    VariantProps<typeof inputVariants> {
  error?: string;
  label?: string;
  helperText?: string;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, variant, size, error, label, helperText, id, ...props }, ref) => {
    const textareaId = id || `textarea-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = !!error || variant === "error";
    const effectiveVariant = hasError ? "error" : variant;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
          >
            {label}
          </label>
        )}

        <textarea
          ref={ref}
          id={textareaId}
          className={cn(
            inputVariants({ variant: effectiveVariant, size }),
            "resize-y min-h-[80px]",
            className
          )}
          aria-invalid={hasError}
          {...props}
        />

        {error && <p className="mt-1.5 text-sm text-danger-600 dark:text-danger-400">{error}</p>}

        {helperText && !error && (
          <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = "Textarea";

// ============================================================================
// Select Component
// ============================================================================

interface SelectProps
  extends
    Omit<SelectHTMLAttributes<HTMLSelectElement>, "size">,
    VariantProps<typeof inputVariants> {
  error?: string;
  label?: string;
  helperText?: string;
  placeholder?: string;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  (
    { className, variant, size, error, label, helperText, id, placeholder, children, ...props },
    ref
  ) => {
    const selectId = id || `select-${Math.random().toString(36).substr(2, 9)}`;
    const hasError = !!error || variant === "error";
    const effectiveVariant = hasError ? "error" : variant;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
          >
            {label}
          </label>
        )}

        <div className="relative">
          <select
            ref={ref}
            id={selectId}
            className={cn(
              inputVariants({ variant: effectiveVariant, size }),
              "appearance-none pr-10 bg-no-repeat bg-right",
              "bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%236b7280%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22M6%208l4%204%204-4%22%2F%3E%3C%2Fsvg%3E')]",
              "dark:bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20fill%3D%22none%22%20viewBox%3D%220%200%2020%2020%22%3E%3Cpath%20stroke%3D%22%239ca3af%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%20stroke-width%3D%221.5%22%20d%3D%22M6%208l4%204%204-4%22%2F%3E%3C%2Fsvg%3E')]",
              "bg-[length:1.25rem_1.25rem]",
              className
            )}
            aria-invalid={hasError}
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {children}
          </select>
        </div>

        {error && <p className="mt-1.5 text-sm text-danger-600 dark:text-danger-400">{error}</p>}

        {helperText && !error && (
          <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400">{helperText}</p>
        )}
      </div>
    );
  }
);

Select.displayName = "Select";

// ============================================================================
// Checkbox Component
// ============================================================================

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const checkboxId = id || `checkbox-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className="w-full">
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            ref={ref}
            id={checkboxId}
            className={cn(
              "mt-0.5 h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-accent-600 dark:text-accent-500",
              "focus:ring-accent-500 dark:focus:ring-accent-500",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              className
            )}
            {...props}
          />
          {label && (
            <label
              htmlFor={checkboxId}
              className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
            >
              {label}
            </label>
          )}
        </div>
        {error && <p className="mt-1.5 text-sm text-danger-600 dark:text-danger-400">{error}</p>}
      </div>
    );
  }
);

Checkbox.displayName = "Checkbox";

// ============================================================================
// Switch Component (Toggle)
// ============================================================================

interface SwitchProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

const Switch = forwardRef<HTMLInputElement, SwitchProps>(
  ({ className, label, id, ...props }, ref) => {
    const switchId = id || `switch-${Math.random().toString(36).substr(2, 9)}`;

    return (
      <div className="flex items-center gap-3">
        <div className="relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer">
          <input type="checkbox" ref={ref} id={switchId} className="peer sr-only" {...props} />
          <div
            className={cn(
              "h-6 w-11 rounded-full bg-gray-200 dark:bg-gray-700",
              "peer-checked:bg-accent-600 dark:peer-checked:bg-accent-500",
              "peer-disabled:opacity-50 peer-disabled:cursor-not-allowed",
              "transition-colors duration-200 ease-in-out",
              className
            )}
          />
          <div
            className={cn(
              "pointer-events-none absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow",
              "transform transition duration-200 ease-in-out",
              "peer-checked:translate-x-5"
            )}
          />
        </div>
        {label && (
          <label
            htmlFor={switchId}
            className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer"
          >
            {label}
          </label>
        )}
      </div>
    );
  }
);

Switch.displayName = "Switch";

export { Input, Textarea, Select, Checkbox, Switch, inputVariants };
export type {
  InputProps,
  TextareaProps,
  SelectProps,
  CheckboxProps,
  SwitchProps,
  InputVariant,
  InputSize,
};
