"use client";

/**
 * Common UI components for SOC Copilot
 * v0.8.2: Extracted from page.tsx for better code organization
 */

import { useState } from "react";

// Loading spinner component
export function Loading() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-soc-600"></div>
    </div>
  );
}

// Error display component
export function Error({ message }: { message: string }) {
  return (
    <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
      <p className="text-red-800">{message}</p>
    </div>
  );
}

// Degraded mode warning component
export function DegradedWarning({ reason }: { reason?: string }) {
  return (
    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
      <p className="text-amber-800 text-sm">
        <span className="font-semibold">⚠️ Degraded mode:</span> The AI response failed validation.
        Some fields may be missing.
        {reason && <span className="ml-2">Reason: {reason}</span>}
      </p>
    </div>
  );
}

// Copy to clipboard button component
export function CopyButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="px-3 py-1.5 text-sm bg-white border border-slate-300 rounded hover:bg-slate-50 transition-colors"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}
