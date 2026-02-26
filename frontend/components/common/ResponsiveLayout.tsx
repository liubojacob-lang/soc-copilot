"use client";

import { useState, useEffect, createContext, useContext, ReactNode } from "react";

// Breakpoint definitions (matching Tailwind defaults)
export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
};

interface ResponsiveContextType {
  width: number;
  height: number;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
  isLargeDesktop: boolean;
  breakpoint: "xs" | "sm" | "md" | "lg" | "xl" | "2xl";
  orientation: "portrait" | "landscape";
  touchDevice: boolean;
}

const ResponsiveContext = createContext<ResponsiveContextType | null>(null);

export function useResponsive() {
  const context = useContext(ResponsiveContext);
  if (!context) {
    throw new Error("useResponsive must be used within a ResponsiveProvider");
  }
  return context;
}

interface ResponsiveProviderProps {
  children: ReactNode;
}

export function ResponsiveProvider({ children }: ResponsiveProviderProps) {
  // Use consistent initial state for SSR - always start with default values
  // to avoid hydration mismatch
  const [dimensions, setDimensions] = useState({
    width: 1024,
    height: 768,
  });
  const [touchDevice, setTouchDevice] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Set mounted flag and update dimensions on client
    setMounted(true);
    setDimensions({
      width: window.innerWidth,
      height: window.innerHeight,
    });
    
    // Detect touch device
    setTouchDevice(
      "ontouchstart" in window || navigator.maxTouchPoints > 0
    );

    const handleResize = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight,
      });
    };

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const { width, height } = dimensions;

  // Determine breakpoint
  const getBreakpoint = (): "xs" | "sm" | "md" | "lg" | "xl" | "2xl" => {
    if (width >= breakpoints["2xl"]) return "2xl";
    if (width >= breakpoints.xl) return "xl";
    if (width >= breakpoints.lg) return "lg";
    if (width >= breakpoints.md) return "md";
    if (width >= breakpoints.sm) return "sm";
    return "xs";
  };

  const value: ResponsiveContextType = {
    width,
    height,
    isMobile: width < breakpoints.md,
    isTablet: width >= breakpoints.md && width < breakpoints.lg,
    isDesktop: width >= breakpoints.lg,
    isLargeDesktop: width >= breakpoints.xl,
    breakpoint: getBreakpoint(),
    orientation: width > height ? "landscape" : "portrait",
    touchDevice,
  };

  return (
    <ResponsiveContext.Provider value={value}>
      {children}
    </ResponsiveContext.Provider>
  );
}

// Responsive wrapper component
interface ResponsiveWrapperProps {
  children: ReactNode;
  mobile?: ReactNode;
  tablet?: ReactNode;
  desktop?: ReactNode;
  className?: string;
}

export function ResponsiveWrapper({
  children,
  mobile,
  tablet,
  desktop,
  className = "",
}: ResponsiveWrapperProps) {
  const { isMobile, isTablet, isDesktop } = useResponsive();

  // Priority: specific > children
  if (isMobile && mobile) return <>{mobile}</>;
  if (isTablet && tablet) return <>{tablet}</>;
  if (isDesktop && desktop) return <>{desktop}</>;

  return <div className={className}>{children}</div>;
}

// Hide on specific breakpoints
interface HideOnProps {
  children: ReactNode;
  mobile?: boolean;
  tablet?: boolean;
  desktop?: boolean;
}

export function HideOn({ children, mobile, tablet, desktop }: HideOnProps) {
  const { isMobile, isTablet, isDesktop } = useResponsive();

  if (mobile && isMobile) return null;
  if (tablet && isTablet) return null;
  if (desktop && isDesktop) return null;

  return <>{children}</>;
}

// Show on specific breakpoints
interface ShowOnProps {
  children: ReactNode;
  mobile?: boolean;
  tablet?: boolean;
  desktop?: boolean;
}

export function ShowOn({ children, mobile, tablet, desktop }: ShowOnProps) {
  const { isMobile, isTablet, isDesktop } = useResponsive();

  if (mobile && isMobile) return <>{children}</>;
  if (tablet && isTablet) return <>{children}</>;
  if (desktop && isDesktop) return <>{children}</>;

  return null;
}

// Touch-friendly button wrapper
interface TouchTargetProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  disabled?: boolean;
}

export function TouchTarget({
  children,
  className = "",
  onClick,
  disabled = false,
}: TouchTargetProps) {
  const { touchDevice } = useResponsive();

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`
        ${touchDevice ? "min-h-[44px] min-w-[44px]" : ""}
        touch-manipulation
        ${className}
      `}
    >
      {children}
    </button>
  );
}

// Responsive grid component
interface ResponsiveGridProps {
  children: ReactNode;
  className?: string;
  cols?: {
    default?: number;
    sm?: number;
    md?: number;
    lg?: number;
    xl?: number;
  };
  gap?: number;
}

export function ResponsiveGrid({
  children,
  className = "",
  cols = { default: 1, sm: 2, md: 3, lg: 4 },
  gap = 4,
}: ResponsiveGridProps) {
  const getGridCols = () => {
    const classes = [];
    if (cols.default) classes.push(`grid-cols-${cols.default}`);
    if (cols.sm) classes.push(`sm:grid-cols-${cols.sm}`);
    if (cols.md) classes.push(`md:grid-cols-${cols.md}`);
    if (cols.lg) classes.push(`lg:grid-cols-${cols.lg}`);
    if (cols.xl) classes.push(`xl:grid-cols-${cols.xl}`);
    return classes.join(" ");
  };

  return (
    <div className={`grid ${getGridCols()} gap-${gap} ${className}`}>
      {children}
    </div>
  );
}

// Responsive spacing component
interface ResponsiveSpacingProps {
  children: ReactNode;
  className?: string;
  padding?: {
    default?: string;
    sm?: string;
    md?: string;
    lg?: string;
  };
  margin?: {
    default?: string;
    sm?: string;
    md?: string;
    lg?: string;
  };
}

export function ResponsiveSpacing({
  children,
  className = "",
  padding = {},
  margin = {},
}: ResponsiveSpacingProps) {
  const getPaddingClasses = () => {
    const classes = [];
    if (padding.default) classes.push(`p-${padding.default}`);
    if (padding.sm) classes.push(`sm:p-${padding.sm}`);
    if (padding.md) classes.push(`md:p-${padding.md}`);
    if (padding.lg) classes.push(`lg:p-${padding.lg}`);
    return classes.join(" ");
  };

  const getMarginClasses = () => {
    const classes = [];
    if (margin.default) classes.push(`m-${margin.default}`);
    if (margin.sm) classes.push(`sm:m-${margin.sm}`);
    if (margin.md) classes.push(`md:m-${margin.md}`);
    if (margin.lg) classes.push(`lg:m-${margin.lg}`);
    return classes.join(" ");
  };

  return (
    <div className={`${getPaddingClasses()} ${getMarginClasses()} ${className}`}>
      {children}
    </div>
  );
}
