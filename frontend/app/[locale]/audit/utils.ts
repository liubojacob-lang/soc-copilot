/** Utility functions for audit logs page */

/** Format date for datetime-local input */
export function formatDateForInput(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Get CSS class for status code
 *
 * 文字必须用 700/800 级，不能用 600 级 —— 徽章底是 100 级浅色（近乎白底），
 * 600 级在其上均不足 WCAG AA 4.5:1（实测 success 3.32、danger 3.95、info 4.24）。
 * 这与下方 getMethodClass 已经是同一约定（它一直用 800 级，因此从未出问题），
 * 本函数此前是唯一的例外。改后实测 6.37–9.45:1。
 *
 * 该约定可推广：**深色字配 100–200 级底；白字配 600–700 级底；500 级只做填充与描边。**
 */
export function getStatusCodeClass(statusCode: number): string {
  if (statusCode >= 200 && statusCode < 300) return "text-success-800 bg-success-100";
  if (statusCode >= 300 && statusCode < 400) return "text-info-800 bg-info-100";
  if (statusCode >= 400 && statusCode < 500) return "text-warning-800 bg-warning-100";
  if (statusCode >= 500) return "text-danger-800 bg-danger-100";
  return "text-primary-700 bg-primary-100";
}

/** Get CSS class for HTTP method */
export function getMethodClass(method: string): string {
  switch (method) {
    case "GET":
      return "bg-info-100 text-info-800";
    case "POST":
      return "bg-success-100 text-success-800";
    case "PUT":
      return "bg-warning-100 text-warning-800";
    case "PATCH":
      return "bg-primary-100 text-primary-700";
    case "DELETE":
      return "bg-danger-100 text-danger-800";
    default:
      return "bg-primary-100 text-primary-700";
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
