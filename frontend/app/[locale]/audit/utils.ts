/** Utility functions for audit logs page */

import type { DatePreset } from "./types";

/** Format date for datetime-local input */
export function formatDateForInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/** Get CSS class for status code */
export function getStatusCodeClass(statusCode: number): string {
  if (statusCode >= 200 && statusCode < 300) return "text-green-600 bg-green-100";
  if (statusCode >= 300 && statusCode < 400) return "text-blue-600 bg-blue-100";
  if (statusCode >= 400 && statusCode < 500) return "text-orange-600 bg-orange-100";
  if (statusCode >= 500) return "text-red-600 bg-red-100";
  return "text-gray-600 bg-gray-100";
}

/** Get CSS class for HTTP method */
export function getMethodClass(method: string): string {
  switch (method) {
    case "GET":
      return "bg-blue-100 text-blue-800";
    case "POST":
      return "bg-green-100 text-green-800";
    case "PUT":
      return "bg-yellow-100 text-yellow-800";
    case "PATCH":
      return "bg-purple-100 text-purple-800";
    case "DELETE":
      return "bg-red-100 text-red-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

/** Generate page numbers for smart pagination */
export function getPageNumbers(page: number, total: number, pageSize: number): (number | string)[] {
  const pages: (number | string)[] = [];
  const totalPages = Math.ceil(total / pageSize);

  if (totalPages <= 7) {
    // Show all pages if 7 or fewer
    for (let i = 1; i <= totalPages; i++) {
      pages.push(i);
    }
  } else {
    // Always show first page
    pages.push(1);

    if (page > 3) {
      pages.push("...");
    }

    // Show pages around current page
    const start = Math.max(2, page - 1);
    const end = Math.min(totalPages - 1, page + 1);

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (page < totalPages - 2) {
      pages.push("...");
    }

    // Always show last page
    pages.push(totalPages);
  }

  return pages;
}

/** Date range presets */
export const datePresets: DatePreset[] = [
  {
    id: "15min",
    name: "🕐 15 min",
    label: "Last 15 minutes",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getTime() - 15 * 60 * 1000);
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(now),
        display: "Last 15 minutes",
      };
    },
  },
  {
    id: "1hour",
    name: "🕐 1 hour",
    label: "Last hour",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getTime() - 60 * 60 * 1000);
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(now),
        display: "Last hour",
      };
    },
  },
  {
    id: "today",
    name: "📅 Today",
    label: "Today",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(now),
        display: "Today",
      };
    },
  },
  {
    id: "yesterday",
    name: "📅 Yesterday",
    label: "Yesterday",
    getRange: () => {
      const now = new Date();
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      const from = new Date(
        yesterday.getFullYear(),
        yesterday.getMonth(),
        yesterday.getDate(),
        0,
        0,
        0
      );
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(
          new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 23, 59, 59)
        ),
        display: "Yesterday",
      };
    },
  },
  {
    id: "7days",
    name: "📊 7 days",
    label: "Last 7 days",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(now),
        display: "Last 7 days",
      };
    },
  },
  {
    id: "30days",
    name: "📊 30 days",
    label: "Last 30 days",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(now),
        display: "Last 30 days",
      };
    },
  },
  {
    id: "thisWeek",
    name: "📊 This week",
    label: "This week",
    getRange: () => {
      const now = new Date();
      const dayOfWeek = now.getDay();
      // Calculate Monday of current week
      const daysFromMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
      const from = new Date(now);
      from.setDate(now.getDate() - daysFromMonday);
      from.setHours(0, 0, 0, 0);
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(now),
        display: "This week",
      };
    },
  },
  {
    id: "thisMonth",
    name: "📊 This month",
    label: "This month",
    getRange: () => {
      const now = new Date();
      const from = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0);
      return {
        from: formatDateForInput(from),
        to: formatDateForInput(now),
        display: "This month",
      };
    },
  },
];
