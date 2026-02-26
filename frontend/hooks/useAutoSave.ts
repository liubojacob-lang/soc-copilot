/**
 * Auto-save hook for form data with localStorage backup.
 * 
 * Features:
 * - Periodic auto-save with configurable interval
 * - Debounced save on data changes
 * - localStorage backup for crash recovery
 * - Unsaved changes warning on page close
 * - Save status tracking
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface AutoSaveOptions<T> {
  data: T;
  saveFunction: (data: T) => Promise<void>;
  interval?: number; // milliseconds
  debounce?: number; // milliseconds
  key: string; // localStorage key for backup
}

interface AutoSaveState {
  isSaving: boolean;
  lastSaved: Date | null;
  hasUnsavedChanges: boolean;
  error: string | null;
}

export function useAutoSave<T>({
  data,
  saveFunction,
  interval = 30000, // 30 seconds
  debounce = 2000, // 2 seconds
  key,
}: AutoSaveOptions<T>): [AutoSaveState, () => Promise<void>, () => void] {
  const [state, setState] = useState<AutoSaveState>({
    isSaving: false,
    lastSaved: null,
    hasUnsavedChanges: false,
    error: null,
  });

  const previousDataRef = useRef<string>(JSON.stringify(data));
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const intervalTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Save to localStorage as backup
  const saveBackup = useCallback(() => {
    try {
      localStorage.setItem(`${key}_backup`, JSON.stringify({
        data,
        timestamp: new Date().toISOString(),
      }));
    } catch (e) {
      console.error('Failed to save backup:', e);
    }
  }, [data, key]);

  // Load backup from localStorage
  const loadBackup = useCallback((): { data: T; timestamp: string } | null => {
    try {
      const backup = localStorage.getItem(`${key}_backup`);
      return backup ? JSON.parse(backup) : null;
    } catch {
      return null;
    }
  }, [key]);

  // Clear backup
  const clearBackup = useCallback(() => {
    localStorage.removeItem(`${key}_backup`);
  }, [key]);

  // Perform save
  const performSave = useCallback(async () => {
    if (state.isSaving) return;
    
    setState(prev => ({ ...prev, isSaving: true, error: null }));
    
    try {
      await saveFunction(data);
      setState(prev => ({
        ...prev,
        isSaving: false,
        lastSaved: new Date(),
        hasUnsavedChanges: false,
      }));
      clearBackup();
    } catch (error) {
      setState(prev => ({
        ...prev,
        isSaving: false,
        error: (error as Error).message,
      }));
      saveBackup(); // Save backup on failure
    }
  }, [data, saveFunction, state.isSaving, clearBackup, saveBackup]);

  // Detect changes
  useEffect(() => {
    const currentData = JSON.stringify(data);
    if (currentData !== previousDataRef.current) {
      previousDataRef.current = currentData;
      setState(prev => ({ ...prev, hasUnsavedChanges: true }));
      
      // Debounced backup save
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        saveBackup();
      }, debounce);
    }
  }, [data, debounce, saveBackup]);

  // Periodic auto-save
  useEffect(() => {
    if (interval > 0) {
      intervalTimerRef.current = setInterval(() => {
        if (state.hasUnsavedChanges) {
          performSave();
        }
      }, interval);
    }
    
    return () => {
      if (intervalTimerRef.current) {
        clearInterval(intervalTimerRef.current);
      }
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [interval, state.hasUnsavedChanges, performSave]);

  // Warn on page close
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (state.hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [state.hasUnsavedChanges]);

  return [state, performSave, clearBackup];
}

// Export utility functions
export const loadAutoSaveBackup = <T>(key: string): { data: T; timestamp: string } | null => {
  try {
    const backup = localStorage.getItem(`${key}_backup`);
    return backup ? JSON.parse(backup) : null;
  } catch {
    return null;
  }
};

export const clearAutoSaveBackup = (key: string): void => {
  localStorage.removeItem(`${key}_backup`);
};