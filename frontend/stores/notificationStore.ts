/**
 * Notification Store
 * Manages application notifications (toasts, alerts)
 */

import { create } from "zustand";

type NotificationType = "success" | "error" | "warning" | "info";

interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  duration?: number;
  createdAt: Date;
}

interface NotificationState {
  notifications: Notification[];
  addNotification: (
    type: NotificationType,
    title: string,
    message: string,
    duration?: number
  ) => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],

  addNotification: (type, title, message, duration = 5000) => {
    const id = Math.random().toString(36).substring(7);
    const notification: Notification = {
      id,
      type,
      title,
      message,
      duration,
      createdAt: new Date(),
    };

    set((state) => ({
      notifications: [...state.notifications, notification],
    }));

    // Auto-remove after duration
    if (duration > 0) {
      setTimeout(() => {
        get().removeNotification(id);
      }, duration);
    }
  },

  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },

  clearAll: () => {
    set({ notifications: [] });
  },
}));

// Convenience functions for common notification types
export const notify = {
  success: (title: string, message: string, duration?: number) => {
    const { addNotification } = useNotificationStore.getState();
    addNotification("success", title, message, duration);
  },

  error: (title: string, message: string, duration?: number) => {
    const { addNotification } = useNotificationStore.getState();
    addNotification("error", title, message, duration);
  },

  warning: (title: string, message: string, duration?: number) => {
    const { addNotification } = useNotificationStore.getState();
    addNotification("warning", title, message, duration);
  },

  info: (title: string, message: string, duration?: number) => {
    const { addNotification } = useNotificationStore.getState();
    addNotification("info", title, message, duration);
  },
};
