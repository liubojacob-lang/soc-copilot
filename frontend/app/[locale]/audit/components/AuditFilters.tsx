/** Audit logs filter component with quick filters and advanced options */

import { useState } from 'react';
import {
  quickFilters,
  getCommonActions,
  getExtendedActions,
  getCommonPaths,
  getExtendedPaths,
  getStatusCodes,
  getExtendedStatusCodes
} from '../constants';
import type { AuditFilters, QuickFilter } from '../types';

interface AuditFiltersProps {
  filters: AuditFilters;
  showAdvanced: boolean;
  onToggleAdvanced: () => void;
  onFiltersChange: (filters: Partial<AuditFilters>) => void;
  onApply: () => void;
  onClear: () => void;
  t: any;
  tPage: any;
}

export function AuditFilters({
  filters,
  showAdvanced,
  onToggleAdvanced,
  onFiltersChange,
  onApply,
  onClear,
  t,
  tPage
}: AuditFiltersProps) {
  const commonActions = getCommonActions(t);
  const extendedActions = getExtendedActions(t);
  const commonPaths = getCommonPaths(t);
  const extendedPaths = getExtendedPaths(t);
  const statusCodes = getStatusCodes(t);
  const extendedStatusCodes = getExtendedStatusCodes(t);

  const applyQuickFilter = (preset: QuickFilter) => {
    onFiltersChange({
      action: preset.filter.filterAction,
      path: preset.filter.filterPath,
      statusCode: preset.filter.filterStatusCode
    });
    onApply();
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow mb-6 overflow-hidden">
      {/* Quick Filters - Always Visible */}
      <div className="p-4 border-b border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Quick Filters
          </h3>
          <button
            onClick={onToggleAdvanced}
            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 flex items-center gap-1 transition-colors"
          >
            {showAdvanced ? "Hide" : "Show"} Advanced
            <svg
              className={`w-3 h-3 transition-transform ${showAdvanced ? "rotate-180" : ""}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {quickFilters.map((preset) => (
            <button
              key={preset.name}
              onClick={() => applyQuickFilter(preset)}
              className="px-4 py-2 text-sm font-medium bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-600 rounded-lg hover:border-blue-400 dark:hover:border-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-all shadow-sm hover:shadow flex items-center gap-1.5"
              title={preset.description}
            >
              <span>{preset.icon}</span>
              <span>{preset.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Filters - Collapsible */}
      {showAdvanced && (
        <div className="p-4 bg-gray-50 dark:bg-gray-800/50 animate-fade-in">
          {/* Basic Filters */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label htmlFor="filterAction" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Action
              </label>
              <ActionFilterDropdown
                value={filters.action}
                onChange={(val: string) => onFiltersChange({ action: val })}
                commonActions={commonActions}
                extendedActions={extendedActions}
                showAdvanced={showAdvanced}
              />
            </div>
            <div>
              <label htmlFor="filterPath" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Path
              </label>
              <PathFilterDropdown
                value={filters.path}
                onChange={(val: string) => onFiltersChange({ path: val })}
                commonPaths={commonPaths}
                extendedPaths={extendedPaths}
                showAdvanced={showAdvanced}
              />
            </div>
            <div>
              <label htmlFor="filterStatusCode" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Status Code
              </label>
              <StatusFilterDropdown
                value={filters.statusCode}
                onChange={(val: string) => onFiltersChange({ statusCode: val })}
                statusCodes={statusCodes}
                extendedStatusCodes={extendedStatusCodes}
                showAdvanced={showAdvanced}
                t={t}
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={onApply}
              className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
              Apply Filters
            </button>
            <button
              onClick={onClear}
              className="px-4 py-2 text-sm font-medium bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-md transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Action Filter Dropdown */
function ActionFilterDropdown({
  value,
  onChange,
  commonActions,
  extendedActions,
  showAdvanced
}: any) {
  return (
    <div className="relative">
      <select
        id="filterAction"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white appearance-none cursor-pointer"
      >
        <optgroup label="Common">
          {commonActions.map((action: any) => (
            <option key={action.value} value={action.value}>
              {action.label}
            </option>
          ))}
        </optgroup>
        {showAdvanced && (
          <optgroup label="More">
            {extendedActions.map((action: any) => (
              <option key={action.value} value={action.value}>
                {action.label}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
}

/** Path Filter Dropdown */
function PathFilterDropdown({
  value,
  onChange,
  commonPaths,
  extendedPaths,
  showAdvanced
}: any) {
  return (
    <div className="relative">
      <select
        id="filterPath"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white appearance-none cursor-pointer"
      >
        <optgroup label="Common">
          {commonPaths.map((path: any) => (
            <option key={path.value} value={path.value}>
              {path.label}
            </option>
          ))}
        </optgroup>
        {showAdvanced && (
          <optgroup label="More">
            {extendedPaths.map((path: any) => (
              <option key={path.value} value={path.value}>
                {path.label}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
}

/** Status Filter Dropdown */
function StatusFilterDropdown({
  value,
  onChange,
  statusCodes,
  extendedStatusCodes,
  showAdvanced,
  t
}: any) {
  return (
    <div className="relative">
      <select
        id="filterStatusCode"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 pr-10 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white appearance-none cursor-pointer"
      >
        <optgroup label="Categories">
          {statusCodes.map((status: any) => (
            <option key={status.value} value={status.value}>
              {status.label}
            </option>
          ))}
        </optgroup>
        {showAdvanced && (
          <optgroup label={t('specificCodes')}>
            {extendedStatusCodes.map((status: any) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </optgroup>
        )}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  );
}
