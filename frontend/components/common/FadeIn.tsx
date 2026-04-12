/**
 * FadeIn - Smooth fade-in animation wrapper
 * Use for smooth content transitions after loading
 */

"use client";

import React, { useEffect, useState } from "react";

interface FadeInProps {
  children: React.ReactNode;
  delay?: number; // Delay in ms
  duration?: number; // Animation duration in ms
  className?: string;
}

export function FadeIn({ children, delay = 0, duration = 300, className = "" }: FadeInProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={`transition-opacity duration-${duration} ${className}`}
      style={{
        opacity: isVisible ? 1 : 0,
        transitionDuration: `${duration}ms`,
        transitionProperty: "opacity",
        transitionTimingFunction: "ease-in-out",
      }}
    >
      {children}
    </div>
  );
}

/**
 * FadeInUp - Fade in with slide up animation
 */
interface FadeInUpProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  distance?: number; // Pixels to slide up
  className?: string;
}

export function FadeInUp({
  children,
  delay = 0,
  duration = 300,
  distance = 20,
  className = "",
}: FadeInUpProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, delay);

    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={className}
      style={{
        opacity: isVisible ? 1 : 0,
        transform: isVisible ? "translateY(0)" : `translateY(${distance}px)`,
        transitionDuration: `${duration}ms`,
        transitionProperty: "opacity, transform",
        transitionTimingFunction: "ease-out",
      }}
    >
      {children}
    </div>
  );
}

/**
 * StaggerChildren - Animate children with staggered delays
 */
interface StaggerChildrenProps {
  children: React.ReactNode;
  staggerDelay?: number; // Delay between each child in ms
  className?: string;
}

export function StaggerChildren({
  children,
  staggerDelay = 100,
  className = "",
}: StaggerChildrenProps) {
  const childrenArray = React.Children.toArray(children);

  return (
    <div className={className}>
      {childrenArray.map((child, index) => (
        <FadeIn key={index} delay={index * staggerDelay}>
          {child}
        </FadeIn>
      ))}
    </div>
  );
}
