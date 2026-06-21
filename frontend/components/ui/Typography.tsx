"use client";

import { type HTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

// Typography token mapping from designTokens.ts / tailwind.config.ts
const variantClasses = {
  display: "text-display font-medium leading-[1.2]",
  h1: "text-h1 font-semibold leading-[1.3]",
  h2: "text-h2 font-semibold leading-[1.4]",
  h3: "text-h3 font-medium leading-[1.5]",
  body: "text-body font-normal leading-[1.5]",
  small: "text-small font-normal leading-[1.5]",
  caption: "text-caption font-normal leading-[1.4]",
} as const;

const colorClasses = {
  primary: "text-text-primary",
  secondary: "text-text-secondary",
  tertiary: "text-text-tertiary",
  disabled: "text-text-disabled",
  inverse: "text-text-inverse",
  link: "text-text-link",
  mono: "text-text-mono",
} as const;

type Variant = keyof typeof variantClasses;
type Color = keyof typeof colorClasses;

// ============================================================
// Heading
// ============================================================
interface HeadingProps extends HTMLAttributes<HTMLHeadingElement> {
  level?: 1 | 2 | 3 | "display";
  color?: Color;
}

export const Heading = forwardRef<HTMLHeadingElement, HeadingProps>(
  ({ level = 1, color = "primary", className, children, ...props }, ref) => {
    const variant: Variant = level === "display" ? "display" : (`h${level}` as Variant);
    const Tag = level === "display" ? "h1" : (`h${level}` as "h1" | "h2" | "h3");

    return (
      <Tag
        ref={ref}
        className={cn(variantClasses[variant], colorClasses[color], className)}
        {...props}
      >
        {children}
      </Tag>
    );
  }
);
Heading.displayName = "Heading";

// ============================================================
// Text
// ============================================================
interface TextProps extends HTMLAttributes<HTMLParagraphElement> {
  color?: Color;
}

export const Text = forwardRef<HTMLParagraphElement, TextProps>(
  ({ color = "primary", className, children, ...props }, ref) => (
    <p ref={ref} className={cn(variantClasses.body, colorClasses[color], className)} {...props}>
      {children}
    </p>
  )
);
Text.displayName = "Text";

// ============================================================
// Caption
// ============================================================
interface CaptionProps extends HTMLAttributes<HTMLSpanElement> {
  color?: Color;
}

export const Caption = forwardRef<HTMLSpanElement, CaptionProps>(
  ({ color = "tertiary", className, children, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(variantClasses.caption, colorClasses[color], className)}
      {...props}
    >
      {children}
    </span>
  )
);
Caption.displayName = "Caption";

// ============================================================
// DataText (monospace)
// ============================================================
interface DataTextProps extends HTMLAttributes<HTMLSpanElement> {
  color?: Color;
}

export const DataText = forwardRef<HTMLSpanElement, DataTextProps>(
  ({ color = "mono", className, children, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(variantClasses.body, colorClasses[color], "font-mono", className)}
      {...props}
    >
      {children}
    </span>
  )
);
DataText.displayName = "DataText";
