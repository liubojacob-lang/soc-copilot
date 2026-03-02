/**
 * SOC Copilot Design System Tokens
 * Centralized design constants for consistent UI
 */

export const DESIGN_TOKENS = {
  borderRadius: {
    xs: '0.25rem',
    sm: '0.375rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    '2xl': '1.5rem',
    full: '9999px',
  },

  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem',
  },

  transitions: {
    fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
    base: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
    slow: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  },

  shadows: {
    soft: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    card: '0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05)',
    elevated: '0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.08)',
  },

  zIndex: {
    dropdown: 50,
    sticky: 100,
    fixed: 200,
    modalBackdrop: 400,
    modal: 500,
    popover: 600,
    toast: 700,
    tooltip: 800,
  },

  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
    '2xl': '1536px',
  },

  touchTarget: {
    min: '44px',
  },
} as const;

export type DesignTokens = typeof DESIGN_TOKENS;
export type BorderRadius = keyof DesignTokens['borderRadius'];
export type Spacing = keyof DesignTokens['spacing'];
export type Transition = keyof DesignTokens['transitions'];
export type Shadow = keyof DesignTokens['shadows'];
export type ZIndex = keyof DesignTokens['zIndex'];

export default DESIGN_TOKENS;
