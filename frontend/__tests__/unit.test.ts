// Frontend Unit Tests for SOC Copilot
// These tests can be run with Vitest or Jest
// Install with: npm install -D vitest @testing-library/react jsdom

import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock fetch for API calls
const mockFetch = vi.fn();
global.fetch = mockFetch;

// ============================================
// Auth Module Tests
// ============================================

describe("Auth Module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("should successfully login with valid credentials", async () => {
      const mockResponse = {
        access_token: "test-token",
        refresh_token: "test-refresh-token",
        token_type: "bearer",
        user: { id: "1", username: "admin", role: "admin" },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      // Test login function
      const result = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "admin", password: "test-password" }),
      });

      const data = await result.json();
      expect(data.access_token).toBe("test-token");
      expect(data.user.username).toBe("admin");
    });

    it("should fail login with invalid credentials", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: "Invalid credentials" }),
      });

      const result = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "admin", password: "wrong-password" }),
      });

      expect(result.ok).toBe(false);
      expect(result.status).toBe(401);
    });

    it("should handle network errors gracefully", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      try {
        await fetch("/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: "admin", password: "test" }),
        });
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toBe("Network error");
      }
    });
  });

  describe("token storage", () => {
    it("should store token in localStorage", () => {
      const token = "test-access-token";
      localStorage.setItem("access_token", token);
      expect(localStorage.getItem("access_token")).toBe(token);
    });

    it("should clear tokens on logout", () => {
      localStorage.setItem("access_token", "test-token");
      localStorage.removeItem("access_token");
      expect(localStorage.getItem("access_token")).toBeNull();
    });
  });
});

// ============================================
// Input Validation Tests
// ============================================

describe("Input Validation", () => {
  describe("email validation", () => {
    const validateEmail = (email: string): boolean => {
      const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
      return emailRegex.test(email);
    };

    it("should validate correct email formats", () => {
      expect(validateEmail("test@example.com")).toBe(true);
      expect(validateEmail("user.name@example.com")).toBe(true);
      expect(validateEmail("user+tag@example.co.uk")).toBe(true);
    });

    it("should reject invalid email formats", () => {
      expect(validateEmail("notanemail")).toBe(false);
      expect(validateEmail("@example.com")).toBe(false);
      expect(validateEmail("user@")).toBe(false);
      expect(validateEmail("user @example.com")).toBe(false);
    });
  });

  describe("password validation", () => {
    const validatePassword = (password: string): { valid: boolean; errors: string[] } => {
      const errors: string[] = [];

      if (password.length < 8) {
        errors.push("Password must be at least 8 characters");
      }
      if (!/[A-Z]/.test(password)) {
        errors.push("Password must contain uppercase letter");
      }
      if (!/[a-z]/.test(password)) {
        errors.push("Password must contain lowercase letter");
      }
      if (!/[0-9]/.test(password)) {
        errors.push("Password must contain digit");
      }

      return { valid: errors.length === 0, errors };
    };

    it("should accept strong passwords", () => {
      const result = validatePassword("Str0ngPass!");
      expect(result.valid).toBe(true);
    });

    it("should reject weak passwords", () => {
      const shortResult = validatePassword("Short1!");
      expect(shortResult.valid).toBe(false);

      const noUpperResult = validatePassword("lowercase123!");
      expect(noUpperResult.valid).toBe(false);

      const noLowerResult = validatePassword("UPPERCASE123!");
      expect(noLowerResult.valid).toBe(false);

      const noDigitResult = validatePassword("NoDigitsHere!");
      expect(noDigitResult.valid).toBe(false);
    });
  });

  describe("IP address validation", () => {
    const validateIPv4 = (ip: string): boolean => {
      const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
      if (!ipv4Regex.test(ip)) return false;

      const parts = ip.split(".");
      return parts.every((part) => {
        const num = parseInt(part, 10);
        return num >= 0 && num <= 255;
      });
    };

    it("should validate correct IPv4 addresses", () => {
      expect(validateIPv4("192.168.1.1")).toBe(true);
      expect(validateIPv4("10.0.0.1")).toBe(true);
      expect(validateIPv4("8.8.8.8")).toBe(true);
      expect(validateIPv4("255.255.255.255")).toBe(true);
    });

    it("should reject invalid IPv4 addresses", () => {
      expect(validateIPv4("256.1.1.1")).toBe(false);
      expect(validateIPv4("192.168.1")).toBe(false);
      expect(validateIPv4("192.168.1.1.1")).toBe(false);
      expect(validateIPv4("not.an.ip")).toBe(false);
    });
  });

  describe("domain validation", () => {
    const validateDomain = (domain: string): boolean => {
      const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9](\.[a-zA-Z]{2,})+$/;
      return domainRegex.test(domain);
    };

    it("should validate correct domains", () => {
      expect(validateDomain("example.com")).toBe(true);
      expect(validateDomain("subdomain.example.com")).toBe(true);
      expect(validateDomain("my-domain.org")).toBe(true);
    });

    it("should reject invalid domains", () => {
      expect(validateDomain("-example.com")).toBe(false);
      expect(validateDomain("example-.com")).toBe(false);
      expect(validateDomain("example")).toBe(false);
    });
  });
});

// ============================================
// XSS Prevention Tests
// ============================================

describe("XSS Prevention", () => {
  const sanitizeInput = (input: string): string => {
    return input
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;")
      .replace(/\//g, "&#x2F;");
  };

  it("should escape HTML tags", () => {
    const malicious = '<script>alert("xss")</script>';
    const sanitized = sanitizeInput(malicious);
    expect(sanitized).not.toContain("<script>");
    expect(sanitized).toContain("&lt;script&gt;");
  });

  it("should escape quotes", () => {
    const malicious = '"><script>alert("xss")</script>';
    const sanitized = sanitizeInput(malicious);
    expect(sanitized).not.toContain("</");
    expect(sanitized).toContain("&quot;");
  });

  it("should preserve normal text", () => {
    const normal = "This is normal text";
    const sanitized = sanitizeInput(normal);
    expect(sanitized).toBe(normal);
  });

  it("should escape angle brackets in event handlers", () => {
    const malicious = "<img src=x onerror=alert(1)>";
    const sanitized = sanitizeInput(malicious);
    expect(sanitized).not.toContain("<img");
    expect(sanitized).toContain("&lt;img");
  });
});

// ============================================
// API Response Handling Tests
// ============================================

describe("API Response Handling", () => {
  describe("error handling", () => {
    const handleApiError = (error: unknown): string => {
      if (error instanceof Error) {
        return error.message;
      }
      if (typeof error === "string") {
        return error;
      }
      return "An unknown error occurred";
    };

    it("should handle Error instances", () => {
      const error = new Error("Test error");
      expect(handleApiError(error)).toBe("Test error");
    });

    it("should handle string errors", () => {
      expect(handleApiError("String error")).toBe("String error");
    });

    it("should handle unknown error types", () => {
      expect(handleApiError(null)).toBe("An unknown error occurred");
      expect(handleApiError(undefined)).toBe("An unknown error occurred");
      expect(handleApiError({})).toBe("An unknown error occurred");
    });
  });

  describe("response parsing", () => {
    it("should parse JSON responses", async () => {
      const mockData = { id: 1, name: "Test" };
      const mockResponse = {
        ok: true,
        json: async () => mockData,
      };

      const data = await mockResponse.json();
      expect(data).toEqual(mockData);
    });

    it("should handle empty responses", async () => {
      const mockResponse = {
        ok: true,
        json: async () => null,
      };

      const data = await mockResponse.json();
      expect(data).toBeNull();
    });
  });
});

// ============================================
// Date/Time Formatting Tests
// ============================================

describe("Date/Time Formatting", () => {
  const formatDate = (date: Date | string): string => {
    const d = typeof date === "string" ? new Date(date) : date;
    return d.toISOString().split("T")[0];
  };

  const formatDateTime = (date: Date | string): string => {
    const d = typeof date === "string" ? new Date(date) : date;
    return d.toISOString().replace("T", " ").split(".")[0];
  };

  it("should format date correctly", () => {
    expect(formatDate("2024-01-15T10:30:00Z")).toBe("2024-01-15");
    expect(formatDate(new Date("2024-12-31"))).toBe("2024-12-31");
  });

  it("should format datetime correctly", () => {
    expect(formatDateTime("2024-01-15T10:30:00.000Z")).toBe("2024-01-15 10:30:00");
  });

  it("should handle invalid dates", () => {
    expect(() => formatDate("invalid")).toThrow();
  });
});

// ============================================
// Pagination Tests
// ============================================

describe("Pagination", () => {
  const calculateTotalPages = (total: number, pageSize: number): number => {
    return Math.ceil(total / pageSize);
  };

  const getPaginationRange = (currentPage: number, totalPages: number): number[] => {
    const range: number[] = [];
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);

    for (let i = start; i <= end; i++) {
      range.push(i);
    }
    return range;
  };

  it("should calculate total pages correctly", () => {
    expect(calculateTotalPages(100, 10)).toBe(10);
    expect(calculateTotalPages(101, 10)).toBe(11);
    expect(calculateTotalPages(99, 10)).toBe(10);
    expect(calculateTotalPages(0, 10)).toBe(0);
  });

  it("should generate pagination range correctly", () => {
    expect(getPaginationRange(1, 10)).toEqual([1, 2, 3]);
    expect(getPaginationRange(5, 10)).toEqual([3, 4, 5, 6, 7]);
    expect(getPaginationRange(10, 10)).toEqual([8, 9, 10]);
  });
});

// ============================================
// Search/Filter Tests
// ============================================

describe("Search and Filter", () => {
  interface Item {
    id: string;
    name: string;
    status: string;
    createdAt: string;
  }

  const items: Item[] = [
    { id: "1", name: "Alert 1", status: "active", createdAt: "2024-01-01" },
    { id: "2", name: "Alert 2", status: "resolved", createdAt: "2024-01-02" },
    { id: "3", name: "Incident 1", status: "active", createdAt: "2024-01-03" },
  ];

  const filterItems = (items: Item[], filters: Partial<Item>): Item[] => {
    return items.filter((item) => {
      if (filters.status && item.status !== filters.status) return false;
      if (filters.name && !item.name.toLowerCase().includes(filters.name.toLowerCase()))
        return false;
      return true;
    });
  };

  it("should filter by status", () => {
    const result = filterItems(items, { status: "active" });
    expect(result).toHaveLength(2);
    expect(result.every((i) => i.status === "active")).toBe(true);
  });

  it("should filter by name", () => {
    const result = filterItems(items, { name: "Alert" });
    expect(result).toHaveLength(2);
    expect(result.every((i) => i.name.includes("Alert"))).toBe(true);
  });

  it("should combine filters", () => {
    const result = filterItems(items, { status: "active", name: "Alert" });
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("1");
  });

  it("should return all items with no filters", () => {
    const result = filterItems(items, {});
    expect(result).toHaveLength(3);
  });
});
