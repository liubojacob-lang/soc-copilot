"use client";

import React, { type ReactNode } from "react";
import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";

interface I18nClientProviderProps {
  messages: AbstractIntlMessages;
  locale: string;
  children: ReactNode;
}

/**
 * Client wrapper for NextIntlClientProvider.
 *
 * In Next.js App Router, layout.tsx is a Server Component and cannot pass functions
 * (like onError and getMessageFallback) directly to NextIntlClientProvider across the RSC boundary.
 * Wrapping it here allows robust runtime fallback and non-breaking warning logs on the client.
 */
export function I18nClientProvider({ messages, locale, children }: I18nClientProviderProps) {
  return (
    <NextIntlClientProvider
      messages={messages}
      locale={locale}
      onError={(error) => {
        if (process.env.NODE_ENV === "development") {
          console.warn(`[i18n warning] ${error.message}`);
        }
      }}
      getMessageFallback={({ key, namespace }) => {
        const nestedKey = namespace ? `${namespace}.${key}` : key;
        return key.split(".").pop() || nestedKey;
      }}
    >
      {children}
    </NextIntlClientProvider>
  );
}
