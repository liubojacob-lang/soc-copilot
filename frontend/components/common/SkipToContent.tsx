"use client";

import { useTranslations } from "next-intl";

export function SkipToContent() {
  const t = useTranslations("common");

  const handleSkip = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const mainContent = document.querySelector("main");
    if (mainContent) {
      mainContent.setAttribute("tabindex", "-1");
      mainContent.focus();
      mainContent.removeAttribute("tabindex");
    }
  };

  return (
    <a
      href="#main-content"
      onClick={handleSkip}
      className="fixed left-4 top-4 z-[9999] -translate-y-20 bg-primary-600 text-white px-6 py-3 rounded-lg font-medium shadow-lg transition-transform duration-200 hover:bg-primary-700 focus:translate-y-0 focus:outline-none focus:ring-4 focus:ring-primary-300"
    >
      {t("skipToContent") || "Skip to main content"}
    </a>
  );
}

export default SkipToContent;
