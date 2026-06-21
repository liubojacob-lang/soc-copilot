/**
 * Design Tokens
 * 3 层设计令牌系统（Core → Semantic → Component）
 * 唯一视觉真相源，覆盖颜色、字体、间距、圆角、阴影、边框
 */

// ==================== Core Tokens ====================
// 平台无关的基础物理值（色值 hex、尺寸 px、字体名）

export const coreColors = {
  // Slate 主色板
  slate: {
    50: "#f8fafc",
    100: "#f1f5f9",
    200: "#e2e8f0",
    300: "#cbd5e1",
    400: "#94a3b8",
    500: "#64748b",
    600: "#475569",
    700: "#334155",
    800: "#1e293b",
    900: "#0f172a",
  },
  // 语义色板
  semantic: {
    success: "#059669",
    warning: "#d97706",
    danger: "#dc2626",
    info: "#2563eb",
    neutral: "#64748b",
  },
  // 语义色背景（浅色模式）
  semanticBgLight: {
    success: "#ecfdf5",
    warning: "#fffbeb",
    danger: "#fef2f2",
    info: "#eff6ff",
    neutral: "#f8fafc",
  },
  // 语义色背景（深色模式）
  semanticBgDark: {
    success: "#064e3b",
    warning: "#78350f",
    danger: "#7f1d1d",
    info: "#1e3a8a",
    neutral: "#0f172a",
  },
  // 语义色文字（浅色模式）
  semanticTextLight: {
    success: "#065f46",
    warning: "#92400e",
    danger: "#991b1b",
    info: "#1e40af",
    neutral: "#475569",
  },
  // 语义色文字（深色模式）
  semanticTextDark: {
    success: "#6ee7b7",
    warning: "#fcd34d",
    danger: "#fca5a5",
    info: "#93c5fd",
    neutral: "#94a3b8",
  },
  // 严重程度色板
  severity: {
    critical: "#dc2626",
    high: "#ea580c",
    medium: "#d97706",
    low: "#059669",
    info: "#2563eb",
  },
} as const;

export const coreTypography = {
  fontFamily: {
    sans: "ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    mono: "ui-monospace, SFMono-Regular, Menlo, Monaco, 'Cascadia Code', monospace",
  },
  fontSize: {
    display: { size: "32px", weight: 500, lineHeight: 1.2 },
    h1: { size: "24px", weight: 600, lineHeight: 1.3 },
    h2: { size: "18px", weight: 600, lineHeight: 1.4 },
    h3: { size: "16px", weight: 500, lineHeight: 1.5 },
    body: { size: "14px", weight: 400, lineHeight: 1.5 },
    small: { size: "12px", weight: 400, lineHeight: 1.5 },
    caption: { size: "11px", weight: 400, lineHeight: 1.4 },
  },
} as const;

export const coreSpacing = {
  "0": "0px",
  "1": "4px",
  "2": "8px",
  "3": "12px",
  "4": "16px",
  "5": "20px",
  "6": "24px",
  "8": "32px",
  "10": "40px",
  "12": "48px",
  "16": "64px",
} as const;

export const coreBorderRadius = {
  none: "0px",
  sm: "4px",
  md: "8px",
  lg: "12px",
  full: "9999px",
} as const;

export const coreShadows = {
  none: "none",
  subtle: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
  sm: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
  md: "0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)",
  lg: "0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.08)",
} as const;

export const coreBorders = {
  width: "1px",
  subtleLight: "#e2e8f0",
  subtleDark: "#334155",
  defaultLight: "#cbd5e1",
  defaultDark: "#475569",
  focusLight: "#2563eb",
  focusDark: "#60a5fa",
} as const;

// ==================== Semantic Tokens ====================
// 带有语义含义的抽象值，映射到 Core Tokens

export const semanticTokens = {
  color: {
    // 背景层级
    bgPage: { light: coreColors.slate[50], dark: coreColors.slate[900] },
    bgCard: { light: "#ffffff", dark: coreColors.slate[800] },
    bgHover: { light: coreColors.slate[100], dark: coreColors.slate[700] },
    bgActive: { light: coreColors.slate[200], dark: coreColors.slate[600] },
    bgInput: { light: "#ffffff", dark: coreColors.slate[900] },
    // 文字层级
    textPrimary: { light: coreColors.slate[900], dark: coreColors.slate[100] },
    textSecondary: { light: coreColors.slate[700], dark: coreColors.slate[400] },
    textTertiary: { light: coreColors.slate[500], dark: coreColors.slate[500] },
    textDisabled: { light: coreColors.slate[400], dark: coreColors.slate[600] },
    textInverse: { light: coreColors.slate[50], dark: coreColors.slate[900] },
    textLink: { light: coreColors.semantic.info, dark: "#60a5fa" },
    textMono: { light: coreColors.slate[900], dark: coreColors.slate[100] },
    // 边框
    borderSubtle: { light: coreBorders.subtleLight, dark: coreBorders.subtleDark },
    borderDefault: { light: coreBorders.defaultLight, dark: coreBorders.defaultDark },
    borderFocus: { light: coreBorders.focusLight, dark: coreBorders.focusDark },
  },
  shadow: {
    card: coreShadows.sm,
    cardHover: coreShadows.md,
    dropdown: coreShadows.md,
    modal: coreShadows.lg,
    nav: coreShadows.subtle,
  },
  radius: {
    card: coreBorderRadius.md,
    cardLarge: coreBorderRadius.lg,
    input: coreBorderRadius.md,
    button: coreBorderRadius.md,
    badge: coreBorderRadius.sm,
    tag: coreBorderRadius.sm,
    table: coreBorderRadius.none,
    avatar: coreBorderRadius.full,
  },
  spacing: {
    pagePadding: coreSpacing["12"],
    moduleGap: coreSpacing["6"],
    cardPadding: coreSpacing["4"],
    cardGap: coreSpacing["4"],
    tableRowHeight: "48px",
    navHeight: "56px",
    sidebarWidth: "256px",
  },
} as const;

// ==================== Component Tokens ====================
// 组件级专用值，直接对应组件的样式需求

export const componentTokens = {
  // KPI Card
  kpiCard: {
    radius: semanticTokens.radius.card,
    shadow: semanticTokens.shadow.card,
    padding: semanticTokens.spacing.cardPadding,
    valueSize: coreTypography.fontSize.display,
    labelSize: coreTypography.fontSize.small,
    gap: coreSpacing["2"],
  },
  // Chart Card
  chartCard: {
    radius: semanticTokens.radius.card,
    shadow: semanticTokens.shadow.card,
    padding: semanticTokens.spacing.cardPadding,
    titleSize: coreTypography.fontSize.h2,
  },
  // Data Table
  dataTable: {
    radius: semanticTokens.radius.table,
    rowHeight: semanticTokens.spacing.tableRowHeight,
    rowGap: coreSpacing["0"],
    headerSize: coreTypography.fontSize.body,
    cellSize: coreTypography.fontSize.body,
    borderColor: semanticTokens.color.borderSubtle,
    hoverBg: { light: coreColors.slate[50], dark: coreColors.slate[800] },
  },
  // Navigation
  nav: {
    topHeight: "56px",
    sidebarWidth: semanticTokens.spacing.sidebarWidth,
    sidebarCollapsedWidth: "64px",
    itemPadding: `${coreSpacing["3"]} ${coreSpacing["4"]}`,
    activeIndicator: "3px",
    activeIndicatorColor: coreColors.semantic.info,
  },
  // Button
  button: {
    radius: semanticTokens.radius.button,
    padding: {
      sm: `${coreSpacing["2"]} ${coreSpacing["3"]}`,
      md: `${coreSpacing["2"]} ${coreSpacing["4"]}`,
      lg: `${coreSpacing["3"]} ${coreSpacing["6"]}`,
    },
    pressScale: "0.98",
    pressDuration: "100ms",
  },
  // Badge
  badge: {
    radius: semanticTokens.radius.badge,
    padding: `${coreSpacing["1"]} ${coreSpacing["2"]}`,
    size: coreTypography.fontSize.small,
  },
  // Input
  input: {
    radius: semanticTokens.radius.input,
    borderWidth: coreBorders.width,
    borderColor: semanticTokens.color.borderDefault,
    focusBorderColor: semanticTokens.color.borderFocus,
    bg: semanticTokens.color.bgInput,
    padding: `${coreSpacing["3"]} ${coreSpacing["4"]}`,
  },
  // Modal / Dropdown
  overlay: {
    radius: semanticTokens.radius.cardLarge,
    shadow: semanticTokens.shadow.modal,
    padding: coreSpacing["6"],
  },
  // Tooltip
  tooltip: {
    radius: semanticTokens.radius.card,
    shadow: semanticTokens.shadow.card,
    padding: coreSpacing["3"],
    bg: semanticTokens.color.bgCard,
    size: coreTypography.fontSize.small,
  },
  // Empty State
  emptyState: {
    iconSize: "64px",
    iconColor: semanticTokens.color.textTertiary,
    titleSize: coreTypography.fontSize.h3,
    descSize: coreTypography.fontSize.body,
  },
  // Status Indicator
  status: {
    dotSize: "8px",
    size: coreTypography.fontSize.small,
  },
} as const;

// ==================== Dark Mode Helpers ====================

export type ThemeMode = "light" | "dark";

export function getSemanticColor(
  token: keyof typeof semanticTokens.color,
  mode: ThemeMode
): string {
  const value = semanticTokens.color[token];
  return value[mode];
}

export function getSemanticShadow(token: keyof typeof semanticTokens.shadow): string {
  return semanticTokens.shadow[token];
}

export function getComponentToken<T extends keyof typeof componentTokens>(
  component: T
): (typeof componentTokens)[T] {
  return componentTokens[component];
}

// ==================== Re-exports for convenience ====================

export const colors = coreColors;
export const typography = coreTypography;
export const spacing = coreSpacing;
export const borderRadius = coreBorderRadius;
export const shadows = coreShadows;
export const borders = coreBorders;

// ==================== Legacy Compatibility ====================
// 旧 patterns / transitions API 兼容层，映射到新设计系统的 Tailwind 类名

export const patterns = {
  button: {
    base: "relative inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-600 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
    variants: {
      primary: "bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800",
      secondary: "bg-surface-hover text-text-primary hover:bg-surface-active",
      ghost: "bg-transparent text-text-primary hover:bg-surface-hover",
      danger: "bg-danger-600 text-white hover:bg-danger-700 active:bg-danger-800",
      outline:
        "border border-border-default bg-transparent text-text-primary hover:bg-surface-hover",
    },
    sizes: {
      sm: "h-8 px-3 text-sm rounded-md",
      md: "h-10 px-4 text-sm rounded-md",
      lg: "h-12 px-6 text-base rounded-md",
    },
  },
  card: {
    base: "bg-surface-card border border-border-subtle",
    shadow: "shadow-sm",
    hover: "hover:bg-surface-hover transition-colors duration-200",
    border: "border border-border-subtle",
    padding: {
      sm: "p-3",
      md: "p-4",
      lg: "p-6",
    },
  },
} as const;

export const transitions = {
  default: "all 150ms ease-out",
  fast: "all 100ms ease-out",
  slow: "all 200ms ease-out",
} as const;

// Type exports
export type CoreColorToken = keyof typeof coreColors;
export type SemanticColorToken = keyof typeof semanticTokens.color;
export type ComponentToken = keyof typeof componentTokens;
export type SeverityLevel = keyof typeof coreColors.severity;
export type SpacingToken = keyof typeof coreSpacing;
export type BorderRadiusToken = keyof typeof coreBorderRadius;
export type ShadowToken = keyof typeof coreShadows;
export type FontSizeToken = keyof typeof coreTypography.fontSize;
