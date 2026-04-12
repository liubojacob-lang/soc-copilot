/**
 * Test Data Utilities for E2E Tests
 *
 * Provides factory functions for generating test data.
 */

import { faker } from "@faker-js/faker";

/**
 * Generate a test user
 */
export function generateTestUser(overrides?: Partial<TestUser>): TestUser {
  return {
    username: faker.internet.username(),
    email: faker.internet.email(),
    password: "TestPassword123!", // Consistent password for testing
    role: "analyst",
    ...overrides,
  };
}

/**
 * Generate a test alert
 */
export function generateTestAlert(overrides?: Partial<TestAlert>): TestAlert {
  return {
    title: faker.lorem.sentence(),
    description: faker.lorem.paragraph(),
    severity: faker.helpers.arrayElement(["low", "medium", "high", "critical"]),
    status: "new",
    source: faker.helpers.arrayElement(["SIEM", "EDR", "IDS", "Firewall"]),
    iocs: generateTestIOCs(faker.number.int({ min: 1, max: 5 })),
    timestamp: faker.date.recent().toISOString(),
    ...overrides,
  };
}

/**
 * Generate test IOCs
 */
export function generateTestIOCs(count: number): TestIOC[] {
  const iocs: TestIOC[] = [];
  const types: Array<"ip" | "domain" | "url" | "hash"> = ["ip", "domain", "url", "hash"];

  for (let i = 0; i < count; i++) {
    const type = faker.helpers.arrayElement(types);
    let value: string;

    switch (type) {
      case "ip":
        value = faker.internet.ipv4();
        break;
      case "domain":
        value = faker.internet.domainName();
        break;
      case "url":
        value = faker.internet.url();
        break;
      case "hash":
        value = faker.string.hexadecimal({ length: 32, prefix: "" });
        break;
      default:
        value = faker.string.sample(10);
    }

    iocs.push({
      type,
      value,
      threat_level: faker.helpers.arrayElement(["benign", "suspicious", "malicious"]),
    });
  }

  return iocs;
}

/**
 * Generate a test playbook
 */
export function generateTestPlaybook(overrides?: Partial<TestPlaybook>): TestPlaybook {
  return {
    name: faker.lorem.words(3),
    description: faker.lorem.paragraph(),
    steps: [
      {
        id: faker.string.uuid(),
        name: "Extract IOCs",
        type: "extract_iocs",
        config: {},
      },
      {
        id: faker.string.uuid(),
        name: "OTX Lookup",
        type: "otx_lookup",
        config: {},
      },
      {
        id: faker.string.uuid(),
        name: "Risk Score",
        type: "risk_score",
        config: {},
      },
    ],
    ...overrides,
  };
}

/**
 * Wait for condition with timeout
 */
export async function waitForCondition(
  condition: () => boolean | Promise<boolean>,
  options: { timeout?: number; interval?: number } = {}
): Promise<void> {
  const { timeout = 30000, interval = 500 } = options;

  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }

  throw new Error(`Condition not met within ${timeout}ms`);
}

/**
 * Retry function with exponential backoff
 */
export async function retry<T>(
  fn: () => Promise<T>,
  options: { maxRetries?: number; initialDelay?: number; maxDelay?: number } = {}
): Promise<T> {
  const { maxRetries = 3, initialDelay = 1000, maxDelay = 10000 } = options;
  let lastError: Error | undefined;

  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (i < maxRetries) {
        const delay = Math.min(initialDelay * Math.pow(2, i), maxDelay);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

/**
 * Type definitions
 */
export interface TestUser {
  username: string;
  email: string;
  password: string;
  role: "admin" | "analyst" | "auditor";
}

export interface TestAlert {
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "new" | "in_progress" | "resolved" | "closed";
  source: string;
  iocs: TestIOC[];
  timestamp: string;
}

export interface TestIOC {
  type: "ip" | "domain" | "url" | "hash";
  value: string;
  threat_level: "benign" | "suspicious" | "malicious";
}

export interface TestPlaybook {
  name: string;
  description: string;
  steps: Array<{
    id: string;
    name: string;
    type: string;
    config: Record<string, unknown>;
  }>;
}
