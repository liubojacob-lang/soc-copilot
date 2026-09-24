"use client";

import { useEffect, useRef, useCallback } from "react";

/**
 * useFocusTrap Hook
 *
 * Traps keyboard focus within a container element (e.g., Modal, Drawer).
 *
 * Features:
 * - Saves focus before opening, restores on close
 * - Moves focus to the first focusable element on open
 * - Tab / Shift+Tab cycles focus within the container
 * - Escape key callback for closing
 *
 * @param isOpen - Whether the focus trap should be active
 * @param onClose - Called when Escape is pressed
 * @param containerRef - Ref to the focus trap container element (optional, defaults to document.activeElement's closest)
 */
export function useFocusTrap(
  isOpen: boolean,
  onClose: () => void,
  containerRef?: React.RefObject<HTMLElement | null>
) {
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const internalRef = useRef<HTMLDivElement | null>(null);

  // Resolve the container ref
  const resolvedRef = containerRef || internalRef;

  /**
   * Get all focusable elements within the container
   */
  const getFocusableElements = useCallback((): HTMLElement[] => {
    const container = resolvedRef.current;
    if (!container) return [];

    const focusableSelectors = [
      "a[href]",
      "button:not([disabled])",
      "textarea:not([disabled])",
      "input:not([disabled])",
      "select:not([disabled])",
      '[tabindex]:not([tabindex="-1"])',
    ];

    try {
      const elements = container.querySelectorAll<HTMLElement>(focusableSelectors.join(", "));
      return Array.from(elements).filter((el) => {
        if (el.hasAttribute("disabled")) return false;
        // Check visibility. Note: fixed-position elements have offsetParent === null in DOM specs.
        if (el.offsetParent !== null) return true;
        const rects = el.getClientRects();
        if (rects.length === 0) return false;
        const style = window.getComputedStyle(el);
        return style.display !== "none" && style.visibility !== "hidden";
      });
    } catch {
      return [];
    }
  }, [resolvedRef]);

  useEffect(() => {
    if (!isOpen) {
      // Restore focus when closing
      if (previousFocusRef.current) {
        try {
          previousFocusRef.current.focus();
        } catch {
          // Element may have been removed from DOM
        }
        previousFocusRef.current = null;
      }
      return;
    }

    // Save current focus
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Move focus into the container on the next frame
    const timeout = requestAnimationFrame(() => {
      const focusable = getFocusableElements();
      if (focusable.length > 0) {
        focusable[0].focus();
      }
    });

    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      // Escape to close
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }

      // Tab trap
      if (e.key === "Tab") {
        const focusable = getFocusableElements();
        if (focusable.length === 0) {
          e.preventDefault();
          return;
        }

        const firstFocusable = focusable[0];
        const lastFocusable = focusable[focusable.length - 1];

        if (e.shiftKey) {
          // Shift+Tab: if focus is on first element, wrap to last
          if (document.activeElement === firstFocusable) {
            e.preventDefault();
            lastFocusable.focus();
          }
        } else {
          // Tab: if focus is on last element, wrap to first
          if (document.activeElement === lastFocusable) {
            e.preventDefault();
            firstFocusable.focus();
          }
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      cancelAnimationFrame(timeout);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose, getFocusableElements]);

  return { ref: resolvedRef };
}
