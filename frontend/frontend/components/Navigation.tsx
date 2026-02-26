"use client";

import { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavigationProps {
  title?: string;
  subtitle?: string;
  children?: ReactNode;
}

export default function Navigation({ title, subtitle, children }: NavigationProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <Link href="/en" className="flex items-center px-4">
                <h1 className="text-xl font-bold text-gray-900">SOC Copilot</h1>
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/en/alerts"
                className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                Alerts
              </Link>
              <Link
                href="/en/playbooks"
                className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                Playbooks
              </Link>
              <Link
                href="/en/ai-assistant"
                className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                AI Assistant
              </Link>
              <Link
                href="/en/threat-intel"
                className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                Threat Intel
              </Link>
              <Link
                href="/en/reports"
                className="px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
              >
                Reports
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {title && (
        <div className="bg-white shadow">
          <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
            <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
            {subtitle && (
              <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
            )}
          </div>
        </div>
      )}

      {children && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          {children}
        </div>
      )}
    </div>
  );
}
