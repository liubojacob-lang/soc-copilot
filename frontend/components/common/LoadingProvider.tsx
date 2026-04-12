/**
 * LoadingProvider - Global loading state management
 * Provides consistent loading experience across the app
 */

"use client";

import React, { createContext, useContext, useState, useCallback } from "react";

interface LoadingContextValue {
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  loadingMessage?: string;
  setLoadingMessage: (message?: string) => void;
}

const LoadingContext = createContext<LoadingContextValue | undefined>(undefined);

export function LoadingProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState<string | undefined>();

  const setLoading = useCallback((loading: boolean) => {
    setIsLoading(loading);
  }, []);

  const setLoadingMessageCallback = useCallback((message?: string) => {
    setLoadingMessage(message);
  }, []);

  return (
    <LoadingContext.Provider
      value={{
        isLoading,
        setLoading,
        loadingMessage,
        setLoadingMessage: setLoadingMessageCallback,
      }}
    >
      {children}
    </LoadingContext.Provider>
  );
}

export function useLoading() {
  const context = useContext(LoadingContext);
  if (!context) {
    throw new Error("useLoading must be used within LoadingProvider");
  }
  return context;
}
