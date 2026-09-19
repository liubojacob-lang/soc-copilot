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

/** Get CSS class for status code */
export function getStatusCodeClass(statusCode: number): string {
  if (statusCode >= 200 && statusCode < 300) return "text-success-600 bg-success-100";
  if (statusCode >= 300 && statusCode < 400) return "text-info-600 bg-info-100";
  if (statusCode >= 400 && statusCode < 500) return "text-warning-700 bg-warning-100";
  if (statusCode >= 500) return "text-danger-600 bg-danger-100";
  return "text-primary-600 bg-primary-100";
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
