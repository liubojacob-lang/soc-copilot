"use client";

import React, { useRef, useEffect, KeyboardEvent, ClipboardEvent } from "react";
import { cn } from "@/lib/utils";

interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  length?: number;
  disabled?: boolean;
  autoFocus?: boolean;
  error?: boolean;
  className?: string;
}

export function OtpInput({
  value,
  onChange,
  onComplete,
  length = 6,
  disabled = false,
  autoFocus = true,
  error = false,
  className,
}: OtpInputProps) {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Split value into array of single chars
  const digits = Array.from({ length }, (_, i) => value[i] || "");

  useEffect(() => {
    if (autoFocus && inputRefs.current[0] && !disabled) {
      inputRefs.current[0]?.focus();
    }
  }, [autoFocus, disabled]);

  const setDigit = (index: number, newDigit: string) => {
    const newDigits = [...digits];
    newDigits[index] = newDigit;
    const newValue = newDigits.join("").slice(0, length);
    onChange(newValue);
    if (newValue.length === length && onComplete) {
      onComplete(newValue);
    }
  };

  const handleInputChange = (index: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const cleaned = raw.replace(/\D/g, "");
    if (!cleaned) {
      setDigit(index, "");
      return;
    }

    if (cleaned.length === 1) {
      setDigit(index, cleaned);
      if (index < length - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    } else {
      handlePastedText(cleaned, index);
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace") {
      if (!digits[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
        setDigit(index - 1, "");
      } else {
        setDigit(index, "");
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePastedText = (pastedText: string, startIndex = 0) => {
    const cleaned = pastedText.replace(/\D/g, "");
    if (!cleaned) return;

    const currentDigits = [...digits];
    for (let i = 0; i < cleaned.length && startIndex + i < length; i++) {
      currentDigits[startIndex + i] = cleaned[i];
    }
    const newValue = currentDigits.join("").slice(0, length);
    onChange(newValue);

    const nextIndex = Math.min(startIndex + cleaned.length, length - 1);
    inputRefs.current[nextIndex]?.focus();

    if (newValue.length === length && onComplete) {
      onComplete(newValue);
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>, index: number) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text");
    handlePastedText(pasted, index);
  };

  return (
    <div className={cn("flex items-center justify-center gap-2 sm:gap-2.5 select-none", className)}>
      {digits.map((digit, idx) => (
        <React.Fragment key={idx}>
          {idx === Math.floor(length / 2) && (
            <span
              className="text-gray-300 dark:text-gray-600 font-bold select-none px-0.5 text-lg"
              aria-hidden="true"
            >
              —
            </span>
          )}
          <input
            ref={(el) => {
              inputRefs.current[idx] = el;
            }}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={1}
            value={digit}
            onChange={(e) => handleInputChange(idx, e)}
            onKeyDown={(e) => handleKeyDown(idx, e)}
            onPaste={(e) => handlePaste(e, idx)}
            disabled={disabled}
            aria-label={`Digit ${idx + 1}`}
            className={cn(
              "w-11 h-11 sm:w-12 sm:h-14 text-center font-mono text-xl sm:text-2xl font-bold rounded-xl transition-all duration-150 outline-none",
              "border shadow-subtle",
              error
                ? "border-red-500 bg-red-50/50 dark:bg-red-950/20 text-red-600 dark:text-red-400 ring-2 ring-red-500/20"
                : digit
                  ? "border-accent-500/80 bg-accent-50/20 dark:bg-accent-950/20 text-gray-900 dark:text-white ring-1 ring-accent-500/20"
                  : "border-gray-200 dark:border-gray-700/90 bg-white dark:bg-gray-800/80 text-gray-900 dark:text-white",
              "focus:border-accent-500 focus:ring-2 focus:ring-accent-500/30 focus:bg-accent-50/30 dark:focus:bg-accent-950/30",
              disabled && "opacity-50 cursor-not-allowed bg-gray-100 dark:bg-gray-800"
            )}
          />
        </React.Fragment>
      ))}
    </div>
  );
}
