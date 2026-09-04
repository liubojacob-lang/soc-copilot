"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

export default function BackToTop() {
  const t = useTranslations("common");
  const [isVisible, setIsVisible] = useState(false);
  const throttleRef = useRef<number | null>(null);

  useEffect(() => {
    const toggleVisibility = () => {
      // Show button when scrolled down 300px
      if (window.pageYOffset > 300) {
        setIsVisible(true);
      } else {
        setIsVisible(false);
      }
    };

    const throttledToggle = () => {
      if (!throttleRef.current) {
        throttleRef.current = requestAnimationFrame(() => {
          toggleVisibility();
          throttleRef.current = null;
        });
      }
    };
    window.addEventListener("scroll", throttledToggle);

    // Clean up the event listener
    return () => {
      window.removeEventListener("scroll", throttledToggle);
      if (throttleRef.current) {
        cancelAnimationFrame(throttleRef.current);
      }
    };
  }, []);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  return (
    <>
      {isVisible && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-8 right-8 z-50 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg transition-all duration-300 hover:scale-110 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          aria-label={t("backToTop")}
          title={t("backToTop")}
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 10l7-7m0 0l7 7m-7-7v18"
            />
          </svg>
        </button>
      )}
    </>
  );
}
