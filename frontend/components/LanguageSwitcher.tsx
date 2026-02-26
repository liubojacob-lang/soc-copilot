'use client';

import { useLocale } from 'next-intl';
import { useRouter, usePathname } from '@/i18n/routing';
import { Check, ChevronDown } from 'lucide-react';
import { useState, useEffect, useRef } from 'react';

type LocaleCode = 'en' | 'zh';

const locales: { code: LocaleCode; label: string; flag: string }[] = [
  { code: 'en', label: 'English', flag: 'EN' },
  { code: 'zh', label: '中文', flag: '中' },
];

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const switchLocale = async (newLocale: LocaleCode) => {
    if (isSwitching || newLocale === locale) return;

    setIsSwitching(true);

    // Set cookie to remember user's language preference
    document.cookie = `NEXT_LOCALE=${newLocale};path=/;max-age=${60 * 60 * 24 * 365};SameSite=lax`;

    // Use next-intl router to switch locale - it handles the path automatically
    router.push(pathname, { locale: newLocale });
    setIsOpen(false);

    // Reset switching state after a short delay
    setTimeout(() => setIsSwitching(false), 500);
  };

  const currentLocale = locales.find((l) => l.code === locale);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Escape to close dropdown
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isOpen]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isSwitching}
        className={`flex items-center gap-1 px-2 py-1.5 text-xs rounded transition-colors ${
          isOpen
            ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 font-medium"
            : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
        } ${isSwitching ? 'opacity-50' : ''}`}
      >
        <span className="font-medium">{currentLocale?.flag}</span>
        <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop for mobile */}
          <div
            className="fixed inset-0 z-40 lg:hidden"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Dropdown menu */}
          <div className="absolute right-0 mt-1 w-28 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 py-1">
            {locales.map(({ code, label, flag }) => {
              const isActive = locale === code;
              return (
                <button
                  key={code}
                  onClick={() => switchLocale(code)}
                  disabled={isSwitching || isActive}
                  className={`w-full flex items-center gap-2 px-3 py-2 text-xs transition-colors ${
                    isActive
                      ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  } ${isSwitching ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  <span className="w-4 text-center font-medium">{flag}</span>
                  <span className="flex-1 text-left">{label}</span>
                  {isActive && <Check className="w-3 h-3" />}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
