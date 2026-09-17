"use client";

import { createContext, useContext, useState, useCallback, useMemo, type ReactNode } from "react";

export interface HeaderData {
  title?: ReactNode;
  subtitle?: ReactNode;
  badge?: ReactNode;
  apiStatus?: "healthy" | "checking" | "error";
  actions?: ReactNode;
  backButton?: ReactNode;
}

interface HeaderContextType {
  headerData: HeaderData;
  setHeaderData: (data: HeaderData) => void;
  resetHeaderData: () => void;
}

const HeaderContext = createContext<HeaderContextType | null>(null);

export function HeaderProvider({ children }: { children: ReactNode }) {
  const [headerData, setHeaderDataState] = useState<HeaderData>({});

  const setHeaderData = useCallback((data: HeaderData) => {
    setHeaderDataState((prev) => {
      if (
        prev.title === data.title &&
        prev.badge === data.badge &&
        prev.apiStatus === data.apiStatus &&
        prev.actions === data.actions &&
        prev.backButton === data.backButton &&
        prev.subtitle === data.subtitle
      ) {
        return prev;
      }
      return data;
    });
  }, []);

  const resetHeaderData = useCallback(() => {
    setHeaderDataState((prev) => {
      if (
        !prev.title &&
        !prev.actions &&
        !prev.badge &&
        !prev.apiStatus &&
        !prev.backButton &&
        !prev.subtitle
      ) {
        return prev;
      }
      return {};
    });
  }, []);

  const value = useMemo(
    () => ({
      headerData,
      setHeaderData,
      resetHeaderData,
    }),
    [headerData, setHeaderData, resetHeaderData]
  );

  return <HeaderContext.Provider value={value}>{children}</HeaderContext.Provider>;
}

export function useHeader() {
  return useContext(HeaderContext);
}
