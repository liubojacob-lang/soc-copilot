/**
 * Design Tokens
 * Centralized design system configuration for consistent UI
 */

// ==================== Colors ====================
export const colors = {
  // Primary brand colors
  primary: {
    50: "#eff6ff",
    100: "#dbeafe",
    200: "#bfdbfe",
    300: "#93c5fd",
    400: "#60a5fa",
    500: "#3b82f6",
    600: "#2563eb",
    700: "#1d4ed8",
    800: "#1e40af",
    900: "#1e3a8a",
  },
  // Semantic colors
  semantic: {
    success: "#10b981",
    warning: "#f59e0b",
    danger: "#ef4444",
    info: "#3b82f6",
  },
  // Severity colors (for alerts/security)
  severity: {
    critical: "#dc2626",
    high: "#ea580c",
    medium: "#d97706",
    low: "#65a30d",
    info: "#3b82f6",
  },
  // Grayscale
  gray: {
    50: "#f9fafb",
    100: "#f3f4f6",
    200: "#e5e7eb",
    300: "#d1d5db",
    400: "#9ca3af",
    500: "#6b7280",
    600: "#4b5563",
    700: "#374151",
    800: "#1f2937",
    900: "#111827",
  },
  // Dark mode background colors
  dark: {
    bg: "#111827",
    surface: "#1f2937",
    border: "#374151",
    text: "#f9fafb",
    textMuted: "#9ca3af",
  },
};

// ==================== Spacing ====================
export const spacing = {
  xs: "0.25rem", // 4px
  sm: "0.5rem", // 8px
  md: "1rem", // 16px
  lg: "1.5rem", // 24px
  xl: "2rem", // 32px
  "2xl": "2.5rem", // 40px
  "3xl": "3rem", // 48px
};

// ==================== Border Radius ====================
export const borderRadius = {
  none: "0",
  sm: "0.125rem", // 2px
  md: "0.375rem", // 6px
  lg: "0.5rem", // 8px
  xl: "0.75rem", // 12px
  "2xl": "1rem", // 16px
  full: "9999px",
};

// ==================== Shadows ====================
export const shadows = {
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
  inner: "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)",
  dark: {
    md: "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
    lg: "0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.2)",
  },
};

// ==================== Typography ====================
export const typography = {
  fontFamily: {
    sans: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  },
  fontSize: {
    xs: "0.75rem",
    sm: "0.875rem",
    md: "1rem",
    lg: "1.125rem",
    xl: "1.25rem",
    "2xl": "1.5rem",
    "3xl": "1.875rem",
    "4xl": "2.25rem",
  },
  fontWeight: {
    normal: "400",
    medium: "500",
    semibold: "600",
    bold: "700",
  },
  lineHeight: {
    tight: "1.25",
    normal: "1.5",
    relaxed: "1.625",
  },
};

// ==================== Transitions ====================
export const transitions = {
  fast: "150ms ease-in-out",
  normal: "200ms ease-in-out",
  slow: "300ms ease-in-out",
};

// ==================== Z-Index ====================
export const zIndex = {
  hide: -1,
  base: 0,
  docked: 10,
  dropdown: 1000,
  sticky: 1100,
  banner: 1200,
  overlay: 1300,
  modal: 1400,
  popover: 1500,
  skipLink: 1600,
  toast: 1700,
  tooltip: 1800,
};

// ==================== Common Component Patterns ====================
export const patterns = {
  // Card pattern
  card: {
    base: "bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700",
    hover: "hover:border-gray-300 dark:hover:border-gray-600 transition-colors",
    shadow: "shadow-sm",
    border: "border-gray-200 dark:border-gray-700",
    padding: {
      sm: "p-3",
      md: "p-4",
      lg: "p-6",
    },
  },
  // Button pattern
  button: {
    base: "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
    sizes: {
      sm: "px-3 py-1.5 text-sm",
      md: "px-4 py-2 text-sm",
      lg: "px-6 py-3 text-base",
    },
    variants: {
      primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500",
      secondary:
        "bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500 dark:bg-gray-700 dark:text-gray-100 dark:hover:bg-gray-600",
      danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
      ghost:
        "text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-100 dark:hover:bg-gray-800",
      outline:
        "border border-gray-300 text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-800",
    },
  },
  // Form input pattern
  input: {
    base: "block w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:border-blue-500 focus:ring-blue-500",
    sizes: {
      sm: "px-3 py-1.5 text-sm",
      md: "px-4 py-2 text-base",
      lg: "px-4 py-3 text-lg",
    },
  },
  // Badge pattern
  badge: {
    base: "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
    variants: {
      default: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200",
      success: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
      warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
      danger: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
      info: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    },
  },
  // Status indicator pattern
  status: {
    base: "inline-flex items-center gap-1.5",
    dot: "w-2 h-2 rounded-full",
    variants: {
      online: "text-green-600 dark:text-green-400",
      offline: "text-gray-500 dark:text-gray-400",
      warning: "text-yellow-600 dark:text-yellow-400",
      error: "text-red-600 dark:text-red-400",
    },
  },
};

// ==================== Severity Styles (for alerts) ====================
export const severityStyles = {
  critical: {
    bg: "bg-red-50 dark:bg-red-900/20",
    border: "border-red-200 dark:border-red-800",
    text: "text-red-800 dark:text-red-200",
    icon: "text-red-500",
    badge: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  },
  high: {
    bg: "bg-orange-50 dark:bg-orange-900/20",
    border: "border-orange-200 dark:border-orange-800",
    text: "text-orange-800 dark:text-orange-200",
    icon: "text-orange-500",
    badge: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  },
  medium: {
    bg: "bg-amber-50 dark:bg-amber-900/20",
    border: "border-amber-200 dark:border-amber-800",
    text: "text-amber-800 dark:text-amber-200",
    icon: "text-amber-500",
    badge: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  },
  low: {
    bg: "bg-blue-50 dark:bg-blue-900/20",
    border: "border-blue-200 dark:border-blue-800",
    text: "text-blue-800 dark:text-blue-200",
    icon: "text-blue-500",
    badge: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  },
  info: {
    bg: "bg-gray-50 dark:bg-gray-800/50",
    border: "border-gray-200 dark:border-gray-700",
    text: "text-gray-800 dark:text-gray-200",
    icon: "text-gray-500",
    badge: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200",
  },
};

// ==================== Layout ====================
export const layout = {
  container: {
    sm: "max-w-screen-sm",
    md: "max-w-screen-md",
    lg: "max-w-screen-lg",
    xl: "max-w-screen-xl",
    "2xl": "max-w-screen-2xl",
  },
  grid: {
    1: "grid-cols-1",
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4",
  },
};

// Type exports
export type ColorToken = keyof typeof colors;
export type SpacingToken = keyof typeof spacing;
export type BorderRadiusToken = keyof typeof borderRadius;
export type ShadowToken = keyof typeof shadows;
export type FontSizeToken = keyof typeof typography.fontSize;
export type SeverityLevel = keyof typeof severityStyles;
